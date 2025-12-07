"""
Bot Model
Stores bot definitions with ownership and webhook configuration
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
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
    
    __table_args__ = (
        UniqueConstraint('name', 'owner_user_id', name='unique_bot_name_per_user'),
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
    
    @classmethod
    async def get_by_id(cls, db: AsyncSession, bot_id: uuid.UUID) -> Optional["Bot"]:
        """
        Get bot by ID
        
        Args:
            db: Database session
            bot_id: Bot identifier
            
        Returns:
            Bot object or None if not found
        """
        result = await db.execute(
            select(cls).where(cls.bot_id == bot_id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_owner(cls, db: AsyncSession, owner_user_id) -> List["Bot"]:
        """
        Get all bots owned by a user
        
        Args:
            db: Database session
            owner_user_id: Owner's user ID (UUID or string)
            
        Returns:
            List of Bot objects
        """
        result = await db.execute(
            select(cls).where(cls.owner_user_id == owner_user_id).order_by(cls.created_at.desc())
        )
        return result.scalars().all()
    
    @classmethod
    async def get_by_name_and_owner(cls, db: AsyncSession, name: str, owner_user_id) -> Optional["Bot"]:
        """
        Get bot by name and owner
        
        Args:
            db: Database session
            name: Bot name
            owner_user_id: Owner's user ID (UUID or string)
            
        Returns:
            Bot object or None if not found
        """
        result = await db.execute(
            select(cls).where(cls.name == name, cls.owner_user_id == owner_user_id)
        )
        return result.scalar_one_or_none()
    
    def is_active(self) -> bool:
        """Check if bot is active"""
        return self.status == 'active'
    
    def activate(self):
        """Activate bot"""
        self.status = 'active'
    
    def deactivate(self):
        """Deactivate bot"""
        self.status = 'inactive'