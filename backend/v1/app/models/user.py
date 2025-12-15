"""
User Model
Stores user account information for multi-tenant system
"""

from sqlalchemy import Column, String, Boolean, DateTime, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
import uuid

from app.database import Base


class User(Base):
    """
    User account model
    
    Table: users
    
    Fields:
        user_id: Unique user identifier (PK, UUID auto-generated)
        email: User email (unique)
        password_hash: Hashed password
        is_active: Account active status
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
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
    
    @classmethod
    async def get_by_id(cls, db: AsyncSession, user_id) -> Optional["User"]:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User identifier (UUID or string representation)
            
        Returns:
            User object or None if not found
        """
        result = await db.execute(
            select(cls).where(cls.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str) -> Optional["User"]:
        """
        Get user by email
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            User object or None if not found
        """
        result = await db.execute(
            select(cls).where(cls.email == email)
        )
        return result.scalar_one_or_none()