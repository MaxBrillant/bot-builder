"""
Session Manager
Manages conversation session lifecycle, timeouts, and state
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID
import json
import sys
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.models.audit_log import AuditResult
from app.repositories.audit_log_repository import AuditLogRepository
from app.utils.logger import get_logger
from app.utils.exceptions import (
    SessionExpiredError,
    SessionNotFoundError,
    MaxAutoProgressionError,
    ContextSizeExceededError,
    ConstraintViolationError
)
from app.utils.constants import SessionStatus, SystemConstraints
from app.utils.encryption import get_encryption_service
from app.config import settings

logger = get_logger(__name__)


class SessionManager:
    """
    Manage conversation sessions
    
    Features:
    - Create/retrieve/update/delete sessions
    - One active session per (channel, channel_user_id, bot_id) tuple
    - 30-minute absolute timeout
    - Context management
    - Auto-progression tracking (max 10)
    - Validation attempt tracking
    - Status management (ACTIVE, COMPLETED, EXPIRED, ERROR)
    - Silent session termination on new flow/bot
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = get_logger(__name__)
        self.audit_log = AuditLogRepository(db)
    
    async def create_session(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: UUID,
        flow_id: UUID,
        flow_snapshot: Dict[str, Any]
    ) -> Session:
        """
        Create new session, terminate existing if any
        
        Args:
            channel: Communication channel (whatsapp, sms, telegram, etc.)
            channel_user_id: User identifier in the channel
            bot_id: Bot ID this session belongs to
            flow_id: Flow UUID identifier
            flow_snapshot: Complete flow definition (for version isolation)
        
        Returns:
            New session instance
        
        Note:
            - Silently terminates any existing active session for this (channel, user, bot)
            - Sets expires_at to created_at + 30 minutes (absolute)
        """
        try:
            # Silently terminate any existing active session for this channel+user+bot
            await self._terminate_existing_session(channel, channel_user_id, bot_id)
            
            # Get start_node_id from flow snapshot
            start_node_id = flow_snapshot.get('start_node_id')
            if not start_node_id:
                raise ValueError("Flow snapshot missing start_node_id")
            
            # Calculate expiration time (30 minutes from now, absolute)
            created_at = datetime.now(timezone.utc)
            expires_at = created_at + timedelta(minutes=settings.flow_constraints.session_timeout_minutes)
            
            # Initialize context with flow variables and defaults
            initial_context = self._initialize_context(flow_snapshot)
            
            # Create new session
            session = Session(
                channel=channel,
                channel_user_id=channel_user_id,
                bot_id=bot_id,
                flow_id=flow_id,
                flow_snapshot=flow_snapshot,
                current_node_id=start_node_id,
                context=initial_context,
                status=SessionStatus.ACTIVE.value,
                created_at=created_at,
                expires_at=expires_at,
                auto_progression_count=0,
                validation_attempts=0
            )
            
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            # Mask user ID for logging
            masked_user_id = self.logger.mask_pii(channel_user_id, "user_id")

            self.logger.log_session_event(
                str(session.session_id),
                "created",
                channel=channel,
                channel_user_id=masked_user_id,
                bot_id=str(bot_id),
                flow_id=str(flow_id)
            )

            # Audit log: session created
            await self.audit_log.log_session_event(
                action="session_created",
                session_id=str(session.session_id),
                user_id=masked_user_id,
                bot_id=str(bot_id),
                result=AuditResult.SUCCESS,
                event_metadata={
                    "channel": channel,
                    "flow_id": str(flow_id)
                }
            )

            return session
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Failed to create session: {str(e)}")
            raise
    
    async def _terminate_existing_session(self, channel: str, channel_user_id: str, bot_id: UUID):
        """
        Silently delete existing active session with row locking

        Per specification (Section 8, line 2828):
        "New flow triggered → Old session deleted silently, new ACTIVE session created"

        Args:
            channel: Communication channel
            channel_user_id: User identifier in channel
            bot_id: Bot ID

        Note:
            Uses SELECT FOR UPDATE to prevent race conditions when creating new sessions.
            Commits immediately to release lock before creating new session.
        """
        # Lock existing active session to prevent concurrent modifications
        stmt = (
            select(Session)
            .where(
                Session.channel == channel,
                Session.channel_user_id == channel_user_id,
                Session.bot_id == bot_id,
                Session.status == SessionStatus.ACTIVE.value
            )
            .with_for_update()  # Database-level row lock
        )

        result = await self.db.execute(stmt)
        existing_session = result.scalar_one_or_none()

        if existing_session:
            old_session_id = str(existing_session.session_id)
            masked_user_id = self.logger.mask_pii(channel_user_id, "user_id")

            # Delete the session per specification (not mark as COMPLETED)
            await self.db.delete(existing_session)
            # Commit immediately to release lock before creating new session
            await self.db.commit()

            self.logger.log_session_event(
                old_session_id,
                "deleted_on_new_flow",
                channel=channel,
                channel_user_id=masked_user_id,
                bot_id=str(bot_id)
            )

            # Audit log: session terminated (on new flow start)
            await self.audit_log.log_session_event(
                action="session_terminated_on_new_flow",
                session_id=old_session_id,
                user_id=masked_user_id,
                bot_id=str(bot_id),
                result=AuditResult.SUCCESS,
                event_metadata={"channel": channel}
            )
    
    async def get_active_session(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: UUID
    ) -> Optional[Session]:
        """
        Get active session for specific channel, user, and bot
        
        Args:
            channel: Communication channel
            channel_user_id: User identifier in channel
            bot_id: Bot ID
        
        Returns:
            Active session or None if no active session exists
        """
        stmt = select(Session).where(
            Session.channel == channel,
            Session.channel_user_id == channel_user_id,
            Session.bot_id == bot_id,
            Session.status == SessionStatus.ACTIVE.value
        )
        
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        return session
    
    async def get_session_by_id(self, session_id: UUID) -> Optional[Session]:
        """
        Get session by ID
        
        Args:
            session_id: Session UUID
        
        Returns:
            Session instance or None
        """
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_context(self, session_id: UUID, context: Dict[str, Any]):
        """
        Update session context variables with size validation and array truncation

        Args:
            session_id: Session UUID
            context: New context dictionary

        Raises:
            ContextSizeExceededError: If context exceeds 100KB limit

        Note:
            Does NOT commit - caller's transaction will commit.
            Arrays exceeding 24 items are silently truncated.
        """
        # Truncate arrays FIRST (per spec: silent truncation when writing to context)
        self._truncate_arrays(context)

        # Validate context size (100 KB limit per spec)
        context_json = json.dumps(context, default=str)
        # Use actual UTF-8 byte size, not Python object overhead
        context_size = len(context_json.encode('utf-8'))

        if context_size > SystemConstraints.MAX_CONTEXT_SIZE:
            self.logger.error(
                f"Context size limit exceeded",
                session_id=str(session_id),
                size=context_size,
                limit=SystemConstraints.MAX_CONTEXT_SIZE
            )
            raise ContextSizeExceededError(
                f"Context size ({context_size} bytes) exceeds maximum "
                f"({SystemConstraints.MAX_CONTEXT_SIZE} bytes)"
            )

        # Encrypt context before storing (raw UPDATE bypasses hybrid property)
        encryption = get_encryption_service()
        encrypted_context = encryption.encrypt_json(context)

        # Only update if all validations passed
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(_context_encrypted=encrypted_context)
        )

        await self.db.execute(stmt)
        # No commit - let outer transaction handle it

    async def update_node(self, session_id: UUID, node_id: str):
        """
        Move session to new node
        
        Args:
            session_id: Session UUID
            node_id: New current node ID
            
        Note:
            Does NOT commit - caller's transaction will commit.
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(current_node_id=node_id)
        )
        
        await self.db.execute(stmt)
        # No commit - let outer transaction handle it
    
    async def increment_auto_progression(self, session_id: UUID) -> int:
        """
        Track consecutive nodes without user input (atomic operation)
        
        Args:
            session_id: Session UUID
        
        Returns:
            New auto_progression_count
        
        Raises:
            MaxAutoProgressionError: If limit exceeded
            
        Note:
            Does NOT commit - caller's transaction will commit.
            This prevents detaching the session object during flow execution.
        """
        # Use atomic SQL increment to avoid race conditions
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(auto_progression_count=Session.auto_progression_count + 1)
            .returning(Session.auto_progression_count)
        )
        
        result = await self.db.execute(stmt)
        new_count = result.scalar_one_or_none()
        # No commit here - let outer transaction handle it
        
        if new_count is None:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        if new_count > SystemConstraints.MAX_AUTO_PROGRESSION:
            await self.error_session(session_id)
            raise MaxAutoProgressionError(
                f"Maximum auto-progression limit ({SystemConstraints.MAX_AUTO_PROGRESSION}) exceeded"
            )
        
        return new_count
    
    async def reset_auto_progression(self, session_id: UUID):
        """
        Reset auto-progression counter (at PROMPT/MENU nodes)
        
        Args:
            session_id: Session UUID
            
        Note:
            Does NOT commit - caller's transaction will commit.
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(auto_progression_count=0)
        )
        
        await self.db.execute(stmt)
        # No commit - let outer transaction handle it
    
    async def increment_validation_attempts(self, session_id: UUID) -> int:
        """
        Track validation retry attempts
        
        Args:
            session_id: Session UUID
        
        Returns:
            New validation_attempts count
            
        Note:
            Does NOT commit - caller's transaction will commit.
        """
        session = await self.get_session_by_id(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        new_count = session.validation_attempts + 1
        
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(validation_attempts=new_count)
        )
        
        await self.db.execute(stmt)
        # No commit - let outer transaction handle it
        
        return new_count
    
    async def reset_validation_attempts(self, session_id: UUID):
        """
        Reset validation counter (on success)
        
        Args:
            session_id: Session UUID
            
        Note:
            Does NOT commit - caller's transaction will commit.
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(validation_attempts=0)
        )
        
        await self.db.execute(stmt)
        # No commit - let outer transaction handle it
    
    async def complete_session(self, session_id: UUID):
        """
        Mark session as COMPLETED

        Args:
            session_id: Session UUID
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(
                status=SessionStatus.COMPLETED.value,
                completed_at=datetime.now(timezone.utc)
            )
        )

        await self.db.execute(stmt)
        await self.db.commit()

        self.logger.log_session_event(str(session_id), "completed")

        # Audit log: session completed
        await self.audit_log.log_session_event(
            action="session_completed",
            session_id=str(session_id),
            result=AuditResult.SUCCESS
        )
    
    async def expire_session(self, session_id: UUID):
        """
        Mark session as EXPIRED

        Args:
            session_id: Session UUID
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(
                status=SessionStatus.EXPIRED.value,
                completed_at=datetime.now(timezone.utc)
            )
        )

        await self.db.execute(stmt)
        await self.db.commit()

        self.logger.log_session_event(str(session_id), "expired")

        # Audit log: session expired
        await self.audit_log.log_session_event(
            action="session_expired",
            session_id=str(session_id),
            result=AuditResult.SUCCESS,
            event_metadata={"reason": "timeout"}
        )
    
    async def error_session(self, session_id: UUID):
        """
        Mark session as ERROR

        Args:
            session_id: Session UUID
        """
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(
                status=SessionStatus.ERROR.value,
                completed_at=datetime.now(timezone.utc)
            )
        )

        await self.db.execute(stmt)
        await self.db.commit()

        self.logger.log_session_event(str(session_id), "error")

        # Audit log: session error
        await self.audit_log.log_session_event(
            action="session_error",
            session_id=str(session_id),
            result=AuditResult.FAILED
        )
    
    def _truncate_arrays(self, context: Dict[str, Any]):
        """
        Truncate arrays in context to MAX_ARRAY_LENGTH (silently)

        Args:
            context: Context dictionary to process (modified in-place)

        Note:
            Per spec: "All arrays written to context are enforced to 24 items max and truncated if exceeded"
            This is a silent truncation - no errors raised, arrays just limited to first 24 items.
        """
        for key, value in context.items():
            # Skip internal metadata keys (start with underscore)
            if key.startswith('_'):
                continue

            if isinstance(value, list):
                if len(value) > SystemConstraints.MAX_ARRAY_LENGTH:
                    # Silently truncate to first 24 items
                    context[key] = value[:SystemConstraints.MAX_ARRAY_LENGTH]
                    self.logger.debug(
                        f"Array '{key}' truncated from {len(value)} to {SystemConstraints.MAX_ARRAY_LENGTH} items",
                        key=key,
                        original_length=len(value),
                        truncated_length=SystemConstraints.MAX_ARRAY_LENGTH
                    )

    def check_timeout(self, session: Session) -> bool:
        """
        Check if session has exceeded 30-minute timeout

        Args:
            session: Session instance

        Returns:
            True if session has expired, False otherwise

        Note:
            Timeout is absolute from session creation, not sliding window
        """
        if not session.expires_at:
            return False

        return datetime.now(timezone.utc) > session.expires_at
    
    async def cleanup_expired_sessions(self):
        """
        Mark all expired active sessions as EXPIRED with grace period
        
        This should be called periodically (e.g., background task).
        Uses a 5-second grace period to avoid marking newly created sessions.
        """
        # Add 5-second grace period to avoid marking newly created sessions
        grace_period = timedelta(seconds=5)
        
        stmt = (
            update(Session)
            .where(
                Session.status == SessionStatus.ACTIVE.value,
                Session.expires_at < datetime.now(timezone.utc) - grace_period
            )
            .values(
                status=SessionStatus.EXPIRED.value,
                completed_at=datetime.now(timezone.utc)
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        expired_count = result.rowcount
        if expired_count > 0:
            self.logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return expired_count
    
    async def update_session_state(
        self,
        session_id: UUID,
        node_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Update session node and/or context in single operation with size validation and array truncation

        Args:
            session_id: Session UUID
            node_id: New node ID (optional)
            context: New context (optional)

        Raises:
            ContextSizeExceededError: If context exceeds 100KB limit

        Note:
            Does NOT commit - caller's transaction will commit.
            This prevents detaching session object during flow execution loop.
            Arrays exceeding 24 items are silently truncated.
        """
        values = {}
        if node_id is not None:
            values['current_node_id'] = node_id
        if context is not None:
            # Truncate arrays FIRST (per spec: silent truncation when writing to context)
            self._truncate_arrays(context)

            # Validate context size (critical for data integrity)
            context_json = json.dumps(context, default=str)
            # Use actual UTF-8 byte size, not Python object overhead
            context_size = len(context_json.encode('utf-8'))

            if context_size > SystemConstraints.MAX_CONTEXT_SIZE:
                self.logger.error(
                    f"Context size limit exceeded",
                    session_id=str(session_id),
                    size=context_size,
                    limit=SystemConstraints.MAX_CONTEXT_SIZE
                )
                raise ContextSizeExceededError(
                    f"Context size ({context_size} bytes) exceeds maximum "
                    f"({SystemConstraints.MAX_CONTEXT_SIZE} bytes)"
                )

            # Encrypt context before storing (raw UPDATE bypasses hybrid property)
            encryption = get_encryption_service()
            values['_context_encrypted'] = encryption.encrypt_json(context)

        # Only update if all validations passed
        if values:
            stmt = (
                update(Session)
                .where(Session.session_id == session_id)
                .values(**values)
            )

            await self.db.execute(stmt)
            # No commit - let outer transaction handle it

    def _initialize_context(self, flow_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize session context with flow variables and metadata
        
        Args:
            flow_snapshot: Complete flow definition
        
        Returns:
            Initialized context dictionary with:
            - All flow variables with their default values
            - _flow_variables: Variable metadata (for type conversion)
            - _flow_defaults: Flow defaults (for retry logic)
        """
        context = {}
        
        # Extract flow variables and apply defaults
        variables = flow_snapshot.get('variables', {})
        if variables:
            # Store variable metadata for type conversion
            context['_flow_variables'] = variables
            
            # Initialize each variable with its default value
            for var_name, var_def in variables.items():
                if isinstance(var_def, dict):
                    default_value = var_def.get('default')
                    context[var_name] = default_value
        
        # Store flow defaults for retry logic
        defaults = flow_snapshot.get('defaults', {})
        if defaults:
            context['_flow_defaults'] = defaults
        
        return context