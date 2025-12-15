"""
Flow repository - centralizes all flow queries
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.flow import Flow


class FlowRepository(BaseRepository[Flow]):
    """Flow-specific data access methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Flow)

    async def get_by_name_and_bot(
        self,
        name: str,
        bot_id: UUID
    ) -> Optional[Flow]:
        """
        Get flow by name and bot (for uniqueness checking)

        Args:
            name: Flow name
            bot_id: Bot UUID

        Returns:
            Flow or None if not found
        """
        stmt = select(Flow).where(
            Flow.name == name,
            Flow.bot_id == bot_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bot_flows(self, bot_id: UUID) -> List[Flow]:
        """
        Get all flows for a bot

        Args:
            bot_id: Bot UUID

        Returns:
            List of flows ordered by creation date
        """
        stmt = (
            select(Flow)
            .where(Flow.bot_id == bot_id)
            .order_by(Flow.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_trigger_keyword(
        self,
        bot_id: UUID,
        keyword: str
    ) -> Optional[Flow]:
        """
        Find flow by trigger keyword (for keyword matching)

        Args:
            bot_id: Bot UUID
            keyword: Trigger keyword (case-insensitive)

        Returns:
            Flow with matching keyword or None
        """
        keyword_upper = keyword.upper()

        # Use PostgreSQL's JSONB contains operator
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            func.jsonb_path_exists(
                Flow.trigger_keywords,
                f'$[*] ? (@ == "{keyword_upper}")'
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_wildcard_trigger(self, bot_id: UUID) -> Optional[Flow]:
        """
        Get flow with wildcard trigger (*) for bot

        Args:
            bot_id: Bot UUID

        Returns:
            Flow with wildcard trigger or None
        """
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            func.jsonb_path_exists(
                Flow.trigger_keywords,
                '$[*] ? (@ == "*")'
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_bot_flows(self, bot_id: UUID) -> int:
        """
        Count flows for a bot

        Args:
            bot_id: Bot UUID

        Returns:
            Number of flows
        """
        stmt = select(func.count(Flow.id)).where(Flow.bot_id == bot_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def trigger_keyword_exists(
        self,
        bot_id: UUID,
        keyword: str,
        exclude_flow_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if trigger keyword is already used in bot

        Args:
            bot_id: Bot UUID
            keyword: Keyword to check (case-insensitive)
            exclude_flow_id: Flow ID to exclude from check (for updates)

        Returns:
            True if keyword exists
        """
        keyword_upper = keyword.upper()

        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            func.jsonb_path_exists(
                Flow.trigger_keywords,
                f'$[*] ? (@ == "{keyword_upper}")'
            )
        )

        if exclude_flow_id:
            stmt = stmt.where(Flow.id != exclude_flow_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
