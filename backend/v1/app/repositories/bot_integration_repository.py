"""Bot Integration Repository"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.bot_integration import BotIntegration
from app.utils.constants import IntegrationPlatform, IntegrationStatus


class BotIntegrationRepository(BaseRepository[BotIntegration]):
    """Repository for bot integration queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, BotIntegration)

    async def get_by_bot_and_platform(
        self,
        bot_id: UUID,
        platform: IntegrationPlatform
    ) -> Optional[BotIntegration]:
        """Get integration for bot and platform"""
        platform_value = platform.value if isinstance(platform, IntegrationPlatform) else platform

        stmt = select(BotIntegration).where(
            BotIntegration.bot_id == bot_id,
            BotIntegration.platform == platform_value
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bot_integrations(self, bot_id: UUID) -> List[BotIntegration]:
        """Get all integrations for a bot"""
        stmt = select(BotIntegration).where(BotIntegration.bot_id == bot_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_connected_integrations(self, bot_id: UUID) -> List[BotIntegration]:
        """Get connected integrations for a bot"""
        stmt = select(BotIntegration).where(
            BotIntegration.bot_id == bot_id,
            BotIntegration.status == IntegrationStatus.CONNECTED.value
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_bot_and_platform(
        self,
        bot_id: UUID,
        platform: IntegrationPlatform
    ) -> bool:
        """Delete integration"""
        platform_value = platform.value if isinstance(platform, IntegrationPlatform) else platform

        stmt = delete(BotIntegration).where(
            BotIntegration.bot_id == bot_id,
            BotIntegration.platform == platform_value
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
