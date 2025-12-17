"""
User Model
Stores user account information for multi-tenant system
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    """
    User account model

    Table: users

    Fields:
        user_id: Unique user identifier (PK, UUID auto-generated)
        email: User email (unique)
        password_hash: Hashed password (nullable for OAuth-only users)
        oauth_provider: OAuth provider name (e.g., 'google', 'github')
        oauth_id: OAuth provider's unique user ID
        is_active: Account active status
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    oauth_provider = Column(String(50), nullable=True)  # OAuth provider (e.g., 'google')
    oauth_id = Column(String(255), nullable=True)  # OAuth provider's unique user ID
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Table arguments for indexes and constraints
    __table_args__ = (
        Index('ix_users_oauth_provider_id', 'oauth_provider', 'oauth_id', unique=True),
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