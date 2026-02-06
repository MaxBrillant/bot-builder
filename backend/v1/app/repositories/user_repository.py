"""
User repository - centralizes all user queries
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """User-specific data access methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address (case-insensitive)

        Args:
            email: User email

        Returns:
            User or None if not found
        """
        stmt = select(User).where(func.lower(User.email) == func.lower(email))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered

        Args:
            email: Email to check

        Returns:
            True if email exists
        """
        user = await self.get_by_email(email)
        return user is not None

    async def get_active_by_email(self, email: str) -> Optional[User]:
        """
        Get active user by email (case-insensitive)

        Args:
            email: User email

        Returns:
            Active user or None
        """
        stmt = select(User).where(func.lower(User.email) == func.lower(email), User.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
