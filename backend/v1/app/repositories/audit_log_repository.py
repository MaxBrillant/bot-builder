"""
Audit Log Repository
Database operations for audit logs
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.audit_log import AuditLog, AuditEventType, AuditResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogRepository:
    """Repository for audit log operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        event_type: str,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Create a new audit log entry

        Args:
            event_type: Type of event (use AuditEventType constants)
            action: Specific action taken
            result: Outcome (use AuditResult constants)
            user_id: Masked user identifier (optional)
            resource_type: Type of resource affected (optional)
            resource_id: ID of resource affected (optional)
            metadata: Additional context (optional)

        Returns:
            Created AuditLog instance

        Note:
            - user_id should already be masked before calling this method
            - metadata should not contain sensitive data
        """
        audit_log = AuditLog(
            event_type=event_type,
            action=action,
            result=result,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {}
        )

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log

    async def log_user_action(
        self,
        action: str,
        user_id: str,
        result: str = AuditResult.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log user action

        Args:
            action: Action description (e.g., "message_received", "input_validated")
            user_id: Masked user identifier
            result: Action result
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        return await self.create(
            event_type=AuditEventType.USER_ACTION,
            action=action,
            result=result,
            user_id=user_id,
            metadata=metadata
        )

    async def log_session_event(
        self,
        action: str,
        session_id: str,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        result: str = AuditResult.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log session lifecycle event

        Args:
            action: Event action (e.g., "session_created", "session_completed")
            session_id: Session identifier
            user_id: Masked user identifier (optional)
            bot_id: Bot identifier (optional)
            result: Event result
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        audit_metadata = metadata or {}
        audit_metadata["session_id"] = session_id
        if bot_id:
            audit_metadata["bot_id"] = bot_id

        return await self.create(
            event_type=AuditEventType.SESSION_EVENT,
            action=action,
            result=result,
            user_id=user_id,
            resource_type="session",
            resource_id=session_id,
            metadata=audit_metadata
        )

    async def log_api_call(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        user_id: Optional[str] = None,
        result: str = AuditResult.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log external API call

        Args:
            method: HTTP method
            url: API URL (sensitive data removed)
            status_code: Response status code (optional)
            user_id: Masked user identifier (optional)
            result: Call result
            metadata: Additional context (NO sensitive headers/body)

        Returns:
            Created audit log entry

        Note:
            - URL should not contain sensitive query params
            - metadata should not contain auth headers or tokens
        """
        audit_metadata = metadata or {}
        audit_metadata["method"] = method
        audit_metadata["url"] = url
        if status_code:
            audit_metadata["status_code"] = status_code

        return await self.create(
            event_type=AuditEventType.API_CALL,
            action=f"api_call_{method.lower()}",
            result=result,
            user_id=user_id,
            metadata=audit_metadata
        )

    async def log_validation_failure(
        self,
        node_id: str,
        attempt: int,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log input validation failure

        Args:
            node_id: Node identifier where validation failed
            attempt: Attempt number
            user_id: Masked user identifier
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        audit_metadata = metadata or {}
        audit_metadata["node_id"] = node_id
        audit_metadata["attempt"] = attempt

        return await self.create(
            event_type=AuditEventType.VALIDATION_FAILURE,
            action="input_validation_failed",
            result=AuditResult.FAILED,
            user_id=user_id,
            metadata=audit_metadata
        )

    async def log_authentication(
        self,
        action: str,
        user_id: Optional[str] = None,
        result: str = AuditResult.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log authentication event

        Args:
            action: Auth action (e.g., "login", "logout", "token_refresh")
            user_id: Masked user identifier (optional)
            result: Auth result
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        return await self.create(
            event_type=AuditEventType.AUTHENTICATION,
            action=action,
            result=result,
            user_id=user_id,
            metadata=metadata
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        result: str = AuditResult.BLOCKED,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log security event (sanitization, pattern rejection, rate limiting)

        Args:
            action: Security action (e.g., "input_sanitized", "pattern_rejected", "rate_limited")
            user_id: Masked user identifier (optional)
            result: Event result
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        return await self.create(
            event_type=AuditEventType.SECURITY,
            action=action,
            result=result,
            user_id=user_id,
            metadata=metadata
        )

    async def log_flow_execution(
        self,
        action: str,
        flow_id: str,
        node_id: str,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        result: str = AuditResult.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log flow execution step

        Args:
            action: Flow action (e.g., "node_executed", "route_evaluated")
            flow_id: Flow identifier
            node_id: Current node identifier
            user_id: Masked user identifier (optional)
            bot_id: Bot identifier (optional)
            result: Execution result
            metadata: Additional context

        Returns:
            Created audit log entry
        """
        audit_metadata = metadata or {}
        audit_metadata["flow_id"] = flow_id
        audit_metadata["node_id"] = node_id
        if bot_id:
            audit_metadata["bot_id"] = bot_id

        return await self.create(
            event_type=AuditEventType.FLOW_EXECUTION,
            action=action,
            result=result,
            user_id=user_id,
            resource_type="flow",
            resource_id=flow_id,
            metadata=audit_metadata
        )

    async def get_recent_logs(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[AuditLog]:
        """
        Retrieve recent audit logs with optional filters

        Args:
            limit: Maximum number of logs to return
            event_type: Filter by event type (optional)
            user_id: Filter by user identifier (optional)

        Returns:
            List of audit log entries (most recent first)
        """
        query = select(AuditLog)

        # Apply filters
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        # Order by most recent first, limit results
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_audit_trail(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get complete audit trail for a user

        Args:
            user_id: Masked user identifier
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            limit: Maximum number of entries

        Returns:
            User's audit trail (most recent first)
        """
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        # Apply time range filters
        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()
