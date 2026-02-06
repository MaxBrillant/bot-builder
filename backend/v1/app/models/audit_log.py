"""
Audit Log Model
Comprehensive security audit trail per spec Section 10.8
"""

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid

from app.database import Base


class AuditLog(Base):
    """
    Security audit log for compliance and monitoring

    Table: audit_logs

    Fields:
        id: Unique audit log entry identifier (PK, UUID)
        timestamp: When the event occurred (indexed)
        event_type: Category of event (indexed)
        user_id: Masked channel_user_id or authenticated user_id (indexed, nullable)
        resource_type: Type of resource (bot, flow, session, etc.)
        resource_id: ID of the resource (bot_id, flow_id, session_id, etc.)
        action: Specific action taken (indexed)
        result: Outcome of the action (success, error, blocked)
        event_metadata: Additional context as JSON (optional)

    Event Types:
        - user_action: User interactions (message received, input validation)
        - session_event: Session lifecycle (created, completed, expired, error)
        - api_call: External API calls (without sensitive data)
        - validation_failure: Input validation failures
        - authentication: Auth attempts (login, logout, token refresh)
        - security: Security events (sanitization, pattern rejection, rate limiting)
        - flow_execution: Flow state changes

    Indexes:
        - timestamp (for time-based queries)
        - event_type (for filtering by event category)
        - user_id (for user audit trail)
        - action (for specific action queries)
        - compound index on (event_type, timestamp) for efficient filtering

    Retention:
        - Audit logs should be retained per compliance requirements
        - Consider separate retention policy from application data
        - Implement archival strategy for old logs

    Security:
        - PII (user_id) is pre-masked before storage
        - Sensitive data NEVER stored in metadata
        - No passwords, API keys, credit cards, or raw PII
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)  # Masked channel_user_id or auth user_id
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(255), nullable=True)
    action = Column(String(128), nullable=False, index=True)
    result = Column(String(32), nullable=False)  # success, error, blocked, etc.
    event_metadata = Column(JSONB, nullable=True)

    __table_args__ = (
        # Compound index for efficient event_type + timestamp queries
        Index('idx_audit_event_timestamp', 'event_type', 'timestamp'),
        # Compound index for user audit trails
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        # Compound index for resource lookups ("show all events for session X")
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return (f"<AuditLog(id='{self.id}', event_type='{self.event_type}', "
                f"action='{self.action}', result='{self.result}')>")

    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "result": self.result,
            "event_metadata": self.event_metadata
        }


# Event type constants for consistency
class AuditEventType:
    """Standard audit event types"""
    USER_ACTION = "user_action"
    SESSION_EVENT = "session_event"
    API_CALL = "api_call"
    VALIDATION_FAILURE = "validation_failure"
    AUTHENTICATION = "authentication"
    SECURITY = "security"
    FLOW_EXECUTION = "flow_execution"


# Result constants
class AuditResult:
    """Standard audit results"""
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    FAILED = "failed"
