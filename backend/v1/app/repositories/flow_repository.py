"""
Flow repository - centralizes all flow queries
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.flow import Flow


class FlowRepository(BaseRepository[Flow]):
    """Flow-specific data access methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Flow)

    async def get_by_id_and_bot(
        self,
        flow_id: UUID,
        bot_id: UUID
    ) -> Optional[Flow]:
        """
        Get flow by ID and bot (for ownership verification)

        Args:
            flow_id: Flow UUID
            bot_id: Bot UUID

        Returns:
            Flow or None if not found or not owned by bot
        """
        stmt = select(Flow).where(
            Flow.id == flow_id,
            Flow.bot_id == bot_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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

    async def get_bot_flows(
        self,
        bot_id: UUID,
        offset: int = 0,
        limit: Optional[int] = None,
        order_by: str = "desc"
    ) -> List[Flow]:
        """
        Get flows for a bot with pagination support

        Args:
            bot_id: Bot UUID
            offset: Number of records to skip (default: 0)
            limit: Maximum records to return (default: None for all)
            order_by: Sort order - "asc" for oldest first, "desc" for newest first (default: "desc")

        Returns:
            List of flows ordered by creation date
        """
        stmt = select(Flow).where(Flow.bot_id == bot_id)

        # Apply ordering
        if order_by == "desc":
            stmt = stmt.order_by(Flow.created_at.desc())
        else:
            stmt = stmt.order_by(Flow.created_at.asc())

        stmt = stmt.offset(offset)

        if limit is not None:
            stmt = stmt.limit(limit)

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

        # Use PostgreSQL's JSONB path query with explicit cast to jsonpath
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            text(f"jsonb_path_exists(flows.trigger_keywords, '$[*] ? (@ == \"{keyword_upper}\")'::jsonpath)")
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
            text("jsonb_path_exists(flows.trigger_keywords, '$[*] ? (@ == \"*\")'::jsonpath)")
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
            text(f"jsonb_path_exists(flows.trigger_keywords, '$[*] ? (@ == \"{keyword_upper}\")'::jsonpath)")
        )

        if exclude_flow_id:
            stmt = stmt.where(Flow.id != exclude_flow_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def delete_by_id_and_bot(self, flow_id: UUID, bot_id: UUID) -> bool:
        """
        Delete flow by ID and bot (for ownership verification)

        Args:
            flow_id: Flow UUID
            bot_id: Bot UUID (for ownership check)

        Returns:
            True if flow was deleted, False if not found
        """
        stmt = delete(Flow).where(
            Flow.id == flow_id,
            Flow.bot_id == bot_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
