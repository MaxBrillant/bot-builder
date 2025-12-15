"""
Session Model
Stores active and historical conversation sessions
"""

from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, Index, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid

from app.database import Base
from app.utils.constants import SessionStatus


class Session(Base):
    """
    Conversation session model
    
    Table: sessions
    
    Fields:
        session_id: Unique session identifier (PK, UUID)
        channel: Communication channel (e.g., 'whatsapp', 'telegram')
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
    channel_user_id = Column(String(255), nullable=False, index=True)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.bot_id", ondelete="CASCADE"), nullable=False, index=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    flow_snapshot = Column(JSONB, nullable=False)
    current_node_id = Column(String(96), nullable=False)
    context = Column(JSONB, default=dict, nullable=False)
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
    )

    # Relationships
    bot = relationship("Bot", back_populates="sessions")
    flow = relationship("Flow", back_populates="sessions")

    def __setattr__(self, name, value):
        """Prevent modification of flow_snapshot after session creation"""
        if (name == 'flow_snapshot' and
            hasattr(self, 'flow_snapshot') and
            self.flow_snapshot is not None and
            value != self.flow_snapshot):
            # flow_snapshot already set with different value, prevent modification
            raise ValueError("flow_snapshot is immutable and cannot be modified after session creation")
        super().__setattr__(name, value)
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', channel='{self.channel}', user='{self.channel_user_id}', bot='{self.bot_id}', status='{self.status}')>"
    
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