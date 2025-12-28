"""
Bot Model
Stores bot definitions with ownership and webhook configuration
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base


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
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    webhook_secret = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default='active', index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)

    # WhatsApp/Evolution API integration fields
    evolution_instance_name = Column(String(255), nullable=True, unique=True, index=True)
    evolution_instance_status = Column(String(20), nullable=True, default='disconnected')
    whatsapp_phone_number = Column(String(50), nullable=True)
    whatsapp_connected_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
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

    def __repr__(self):
        return f"<Bot(bot_id='{self.bot_id}', name='{self.name}', owner='{self.owner_user_id}')>"
    
    @property
    def webhook_url(self) -> str:
        """Auto-generated webhook URL per spec line 97"""
        return f"/webhook/{self.bot_id}"
    
    def to_dict(self, include_webhook_secret: bool = False):
        """
        Convert model to dictionary (UUIDs as strings for JSON serialization)
        
        Args:
            include_webhook_secret: Whether to include webhook secret
        
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

        return result

    def is_active(self) -> bool:
        """Check if bot is active"""
        return self.status == 'active'
    
    def activate(self):
        """Activate bot"""
        self.status = 'active'
    
    def deactivate(self):
        """Deactivate bot"""
        self.status = 'inactive'