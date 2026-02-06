"""
User Model
Stores user account information for multi-tenant system
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base
from app.utils.constants import OAuthProvider


class User(Base):
    """
    User account model

    Table: users

    Fields:
        user_id: Unique user identifier (PK, UUID auto-generated)
        email: User email (unique)
        password_hash: Hashed password (nullable for OAuth-only users)
        oauth_provider: OAuth provider name (e.g., 'GOOGLE', 'GITHUB')
        oauth_id: OAuth provider's unique user ID
        is_active: Account active status
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Note: uniqueness enforced via case-insensitive index idx_users_email_unique_lower
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    oauth_provider = Column(String(50), nullable=True)  # OAuth provider (e.g., 'GOOGLE')
    oauth_id = Column(String(255), nullable=True)  # OAuth provider's unique user ID
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Table arguments for indexes and constraints
    __table_args__ = (
        CheckConstraint("oauth_provider IS NULL OR oauth_provider IN ('GOOGLE')", name='check_oauth_provider'),
        Index('ix_users_oauth_provider_id', 'oauth_provider', 'oauth_id', unique=True),
        # Case-insensitive unique email index (prevents user@test.com and USER@test.com as different accounts)
        Index('idx_users_email_unique_lower', text('LOWER(email)'), unique=True),
    )

    # Relationships
    bots = relationship(
        "Bot",
        back_populates="owner",
        lazy="noload",  # Don't load by default
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}')>"
    
    def to_dict(self):
        """Convert model to dictionary (UUID as string)"""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }