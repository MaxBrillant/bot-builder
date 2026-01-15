"""
Bot Model
Stores bot definitions with ownership and webhook configuration
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from app.database import Base
from app.utils.constants import BotStatus, IntegrationStatus

if TYPE_CHECKING:
    from app.models.bot_integration import BotIntegration
    from app.utils.constants import IntegrationPlatform


class Bot(Base):
    """
    Bot definition model
    
    Table: bots
    
    Fields:
        bot_id: Unique bot identifier (PK, UUID)
        owner_user_id: User who owns this bot (FK to users)
        name: Human-readable bot name
        webhook_secret: Secret for webhook authentication
        status: Bot status (active/inactive)
        created_at: Bot creation timestamp
        updated_at: Last update timestamp
    
    Indexes:
        - owner_user_id (for querying user's bots)
        - status (for filtering active bots)
        - updated_at (for sorting)
    
    Constraints:
        - Foreign key to users(user_id) with CASCADE delete
        - Unique (name, owner_user_id) - bot names unique per user
    """
    
    __tablename__ = "bots"
    
    bot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(96), nullable=False)  # Spec line 85: Bot name max 96 characters
    description = Column(String(512), nullable=True)  # Spec line 86: Bot description max 512 characters
    webhook_secret = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=BotStatus.ACTIVE.value, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name='check_bot_status'),
        UniqueConstraint('name', 'owner_user_id', name='unique_bot_name_per_user'),
    )

    # Relationships
    owner = relationship("User", back_populates="bots")
    flows = relationship(
        "Flow",
        back_populates="bot",
        lazy="selectin",  # Eager load flows to solve N+1 queries
        cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session",
        back_populates="bot",
        lazy="noload",  # Don't load by default (too many)
        cascade="all, delete-orphan"
    )
    integrations = relationship(
        "BotIntegration",
        back_populates="bot",
        lazy="selectin",  # Eager load integrations
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Bot(bot_id='{self.bot_id}', name='{self.name}', owner='{self.owner_user_id}')>"
    
    @property
    def webhook_url(self) -> str:
        """Auto-generated webhook URL per spec line 97"""
        return f"/webhook/{self.bot_id}"

    def get_integration(self, platform: 'IntegrationPlatform') -> Optional['BotIntegration']:
        """
        Get integration by platform enum

        Args:
            platform: Platform enum value

        Returns:
            BotIntegration or None
        """
        platform_value = platform.value if hasattr(platform, 'value') else platform
        return next((i for i in self.integrations if i.platform == platform_value), None)

    def has_integration(self, platform: 'IntegrationPlatform') -> bool:
        """Check if bot has integration for platform"""
        return self.get_integration(platform) is not None

    @property
    def active_integrations(self) -> list['BotIntegration']:
        """Get list of connected integrations"""
        return [i for i in self.integrations if i.status == IntegrationStatus.CONNECTED.value]

    def to_dict(self, include_webhook_secret: bool = False, include_integrations: bool = False):
        """
        Convert model to dictionary (UUIDs as strings for JSON serialization)

        Args:
            include_webhook_secret: Whether to include webhook secret
            include_integrations: Whether to include integration details

        Returns:
            Dictionary representation
        """
        result = {
            "bot_id": str(self.bot_id),
            "owner_user_id": str(self.owner_user_id),  # Convert UUID to string
            "name": self.name,
            "description": self.description,
            "webhook_url": self.webhook_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_webhook_secret:
            result["webhook_secret"] = self.webhook_secret

        if include_integrations:
            result["integrations"] = [i.to_dict() for i in self.integrations]

        return result

    def is_active(self) -> bool:
        """Check if bot is active"""
        return self.status == BotStatus.ACTIVE.value

    def activate(self):
        """Activate bot"""
        self.status = BotStatus.ACTIVE.value

    def deactivate(self):
        """Deactivate bot"""
        self.status = BotStatus.INACTIVE.value