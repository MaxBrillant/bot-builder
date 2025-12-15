"""
Bot repository - centralizes all bot queries

Solves N+1 query problems with eager loading of relationships
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.bot import Bot


class BotRepository(BaseRepository[Bot]):
    """Bot-specific data access methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Bot)

    async def get_by_id(self, bot_id: UUID) -> Optional[Bot]:
        """
        Get bot by ID (uses bot_id as primary key)

        Args:
            bot_id: Bot UUID

        Returns:
            Bot or None if not found
        """
        stmt = select(Bot).where(Bot.bot_id == bot_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_flows(self, bot_id: UUID) -> Optional[Bot]:
        """
        Get bot with eager-loaded flows (solves N+1 query problem)

        Args:
            bot_id: Bot UUID

        Returns:
            Bot with flows loaded or None
        """
        stmt = (
            select(Bot)
            .where(Bot.bot_id == bot_id)
            .options(selectinload(Bot.flows))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_bots(self, user_id: UUID) -> List[Bot]:
        """
        Get all bots owned by user with eager-loaded flows (solves N+1)

        Args:
            user_id: Owner user ID

        Returns:
            List of bots with flows loaded
        """
        stmt = (
            select(Bot)
            .where(Bot.owner_user_id == user_id)
            .options(selectinload(Bot.flows))
            .order_by(Bot.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_and_owner(
        self,
        name: str,
        owner_user_id: UUID
    ) -> Optional[Bot]:
        """
        Get bot by name and owner (for uniqueness checking)

        Args:
            name: Bot name
            owner_user_id: Owner user ID

        Returns:
            Bot or None if not found
        """
        stmt = select(Bot).where(
            Bot.name == name,
            Bot.owner_user_id == owner_user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_webhook_secret(
        self,
        bot_id: UUID,
        webhook_secret: str
    ) -> Optional[Bot]:
        """
        Get bot and verify webhook secret (for webhook authentication)

        Args:
            bot_id: Bot UUID
            webhook_secret: Webhook secret to verify

        Returns:
            Bot if ID and secret match, None otherwise
        """
        stmt = select(Bot).where(
            Bot.bot_id == bot_id,
            Bot.webhook_secret == webhook_secret
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_bots(self, user_id: UUID) -> List[Bot]:
        """
        Get active bots for user

        Args:
            user_id: Owner user ID

        Returns:
            List of active bots
        """
        stmt = (
            select(Bot)
            .where(
                Bot.owner_user_id == user_id,
                Bot.status == 'active'
            )
            .options(selectinload(Bot.flows))
            .order_by(Bot.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
