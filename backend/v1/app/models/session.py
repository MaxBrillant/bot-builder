"""
Session Model
Stores active and historical conversation sessions with encrypted PII
"""

from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, Index, ForeignKey, text, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone
import uuid
import json

from app.database import Base
from app.utils.constants import SessionStatus


class Session(Base):
    """
    Conversation session model

    Table: sessions

    Fields:
        session_id: Unique session identifier (PK, UUID)
        channel: Communication channel (e.g., 'WHATSAPP', 'TELEGRAM')
        channel_user_id: Platform-specific user identifier (replaces phone_number)
        bot_id: Bot executing this session (FK to bots)
        flow_id: Reference to flow being executed
        flow_snapshot: Complete flow definition at session start (JSONB)
        current_node_id: Current position in flow
        context: Session variables and state (JSONB)
        status: Session lifecycle status (ACTIVE, COMPLETED, EXPIRED, ERROR)
        created_at: Session creation timestamp
        expires_at: Absolute timeout (created_at + 30 minutes)
        completed_at: Session completion timestamp
        auto_progression_count: Tracks consecutive nodes without user input
        validation_attempts: Tracks validation retry attempts
        message_history: Conversation message log with timestamps (JSONB array)

    Indexes:
        - channel_user_id (for session lookup)
        - bot_id (for bot-specific sessions)
        - status (for filtering active sessions)
        - expires_at (for timeout checks on active sessions)
        - flow_id (for flow usage tracking)

    Constraints:
        - Unique (channel, channel_user_id, bot_id) WHERE status = 'ACTIVE'
          Ensures only one active session per user+channel+bot combination
        - CHECK status IN ('ACTIVE', 'COMPLETED', 'EXPIRED', 'ERROR')
        - Foreign key to bots(bot_id) with CASCADE delete
    """
    
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(String(50), nullable=False)

    # channel_user_id: Plaintext for query support (used in WHERE clauses, unique indexes)
    # PII protection via masking in logs, not encryption (encryption breaks lookups)
    channel_user_id = Column(String(255), nullable=False, index=True)

    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.bot_id", ondelete="CASCADE"), nullable=False, index=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)

    # ENCRYPTED FIELD: flow_snapshot (contains flow definition, may have sensitive data)
    # Stored as encrypted bytes, accessed via hybrid property
    _flow_snapshot_encrypted = Column("flow_snapshot", LargeBinary, nullable=False)

    current_node_id = Column(String(96), nullable=False)

    # ENCRYPTED FIELD: context (contains user inputs - PII)
    # Stored as encrypted bytes, accessed via hybrid property
    _context_encrypted = Column("context", LargeBinary, nullable=False)

    status = Column(
        String(20),
        nullable=False,
        index=True,
        server_default='ACTIVE'
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    auto_progression_count = Column(Integer, default=0, nullable=False)
    validation_attempts = Column(Integer, default=0, nullable=False)
    message_history = Column(JSONB, default=lambda: [], nullable=False, server_default='[]')

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'EXPIRED', 'ERROR')",
            name='check_session_status'
        ),
        Index(
            'idx_unique_active_session',
            'channel',
            'channel_user_id',
            'bot_id',
            unique=True,
            postgresql_where=text("status = 'ACTIVE'")
        ),
        Index(
            'idx_sessions_expires',
            'expires_at',
            postgresql_where=text("status = 'ACTIVE'")
        ),
        # Composite index for bot+status filtering (common query pattern)
        Index(
            'idx_sessions_bot_status',
            'bot_id',
            'status'
        ),
        # Index for cleanup queries on completed sessions
        Index(
            'idx_sessions_completed_at',
            'completed_at',
            postgresql_where=text("completed_at IS NOT NULL")
        ),
    )

    # Relationships
    bot = relationship("Bot", back_populates="sessions")
    flow = relationship("Flow", back_populates="sessions")

    # Hybrid properties for transparent encryption/decryption of sensitive fields
    # Note: channel_user_id is NOT encrypted (needed for queries/indexes)

    @hybrid_property
    def flow_snapshot(self) -> dict:
        """Decrypt and return flow_snapshot"""
        from app.utils.encryption import get_encryption_service
        # Access via __dict__ to avoid SQLAlchemy's InstrumentedAttribute for uninitialized columns
        encrypted = self.__dict__.get('_flow_snapshot_encrypted')
        if not isinstance(encrypted, (bytes, str)):
            return None  # Not yet initialized
        encryption = get_encryption_service()
        return encryption.decrypt_json(encrypted)

    @flow_snapshot.setter
    def flow_snapshot(self, value: dict):
        """Encrypt and store flow_snapshot (immutability checked in __setattr__)"""
        from app.utils.encryption import get_encryption_service
        encryption = get_encryption_service()
        self._flow_snapshot_encrypted = encryption.encrypt_json(value)

    @hybrid_property
    def context(self) -> dict:
        """Decrypt and return context"""
        from app.utils.encryption import get_encryption_service
        # Access via __dict__ to avoid SQLAlchemy's InstrumentedAttribute for uninitialized columns
        encrypted = self.__dict__.get('_context_encrypted')
        if not isinstance(encrypted, (bytes, str)):
            return {}  # Not yet initialized
        encryption = get_encryption_service()
        decrypted = encryption.decrypt_json(encrypted)
        return decrypted if decrypted is not None else {}

    @context.setter
    def context(self, value: dict):
        """Encrypt and store context"""
        from app.utils.encryption import get_encryption_service
        encryption = get_encryption_service()
        self._context_encrypted = encryption.encrypt_json(value)

    def __setattr__(self, name, value):
        """Prevent modification of flow_snapshot after session creation"""
        # Check instance __dict__ directly to avoid SQLAlchemy's InstrumentedAttribute descriptor
        # During object construction, _flow_snapshot_encrypted won't be in __dict__ yet
        if name == 'flow_snapshot':
            encrypted = self.__dict__.get('_flow_snapshot_encrypted')
            if isinstance(encrypted, (bytes, str)):
                # flow_snapshot is already set - check if trying to modify
                current = self.flow_snapshot
                if current is not None and value != current:
                    raise ValueError("flow_snapshot is immutable and cannot be modified after session creation")
        super().__setattr__(name, value)
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', channel='{self.channel}', user='{self.channel_user_id}', bot='{self.bot_id}', status='{self.status}')>"

    @property
    def session_key(self) -> str:
        """
        Generate composite session key string per spec line 2780

        Format: "channel:channel_user_id:bot_id"

        This property provides convenient access to the session key format
        documented in the specification, though internally the session uses
        normalized database columns with a unique constraint.

        Returns:
            Composite session key string
        """
        return f"{self.channel}:{self.channel_user_id}:{self.bot_id}"

    def to_dict(self, include_snapshot: bool = False):
        """
        Convert model to dictionary
        
        Args:
            include_snapshot: Whether to include full flow snapshot
        
        Returns:
            Dictionary representation
        """
        result = {
            "session_id": str(self.session_id),
            "channel": self.channel,
            "channel_user_id": self.channel_user_id,
            "bot_id": str(self.bot_id) if self.bot_id else None,
            "flow_id": str(self.flow_id) if self.flow_id else None,
            "current_node_id": self.current_node_id,
            "context": self.context,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "auto_progression_count": self.auto_progression_count,
            "validation_attempts": self.validation_attempts
        }
        
        if include_snapshot:
            result["flow_snapshot"] = self.flow_snapshot
        
        return result
    
    def is_expired(self) -> bool:
        """Check if session has exceeded timeout"""
        return datetime.now(timezone.utc) > self.expires_at if self.expires_at else False
    
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE.value and not self.is_expired()
    
    def mark_completed(self):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED.value
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_expired(self):
        """Mark session as expired"""
        self.status = SessionStatus.EXPIRED.value
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_error(self):
        """Mark session as error"""
        self.status = SessionStatus.ERROR.value
        self.completed_at = datetime.now(timezone.utc)