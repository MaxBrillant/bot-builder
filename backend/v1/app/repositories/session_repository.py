"""
Session repository - centralizes all session queries
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.session import Session
from app.utils.constants import SessionStatus


class SessionRepository(BaseRepository[Session]):
    """Session-specific data access methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)

    async def get_by_id(self, session_id: UUID) -> Optional[Session]:
        """
        Get session by ID

        Args:
            session_id: Session UUID

        Returns:
            Session or None if not found
        """
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_session(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: UUID
    ) -> Optional[Session]:
        """
        Get active session for user+channel+bot combination

        Args:
            channel: Channel identifier (whatsapp, telegram, etc.)
            channel_user_id: Platform-specific user ID
            bot_id: Bot UUID

        Returns:
            Active session or None
        """
        stmt = select(Session).where(
            and_(
                Session.channel == channel,
                Session.channel_user_id == channel_user_id,
                Session.bot_id == bot_id,
                Session.status == SessionStatus.ACTIVE.value
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bot_sessions(
        self,
        bot_id: UUID,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Session]:
        """
        Get sessions for a bot

        Args:
            bot_id: Bot UUID
            status: Optional status filter
            limit: Maximum number of sessions

        Returns:
            List of sessions
        """
        stmt = select(Session).where(Session.bot_id == bot_id)

        if status:
            stmt = stmt.where(Session.status == status)

        stmt = stmt.order_by(Session.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_sessions(
        self,
        limit: int = 1000
    ) -> List[Session]:
        """
        Get active sessions that have expired

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of expired sessions
        """
        now = datetime.now(timezone.utc)

        stmt = (
            select(Session)
            .where(
                and_(
                    Session.status == SessionStatus.ACTIVE.value,
                    Session.expires_at < now
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_expired_sessions(self) -> int:
        """
        Mark expired active sessions as EXPIRED

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)

        # Update expired sessions
        from sqlalchemy import update
        stmt = (
            update(Session)
            .where(
                and_(
                    Session.status == SessionStatus.ACTIVE.value,
                    Session.expires_at < now
                )
            )
            .values(
                status=SessionStatus.EXPIRED.value,
                completed_at=now
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_old_sessions(
        self,
        days_old: int = 30
    ) -> int:
        """
        Delete completed/expired sessions older than specified days

        Args:
            days_old: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        stmt = delete(Session).where(
            and_(
                Session.status.in_([
                    SessionStatus.COMPLETED.value,
                    SessionStatus.EXPIRED.value,
                    SessionStatus.ERROR.value
                ]),
                Session.completed_at < cutoff_date
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def count_active_sessions(self, bot_id: Optional[UUID] = None) -> int:
        """
        Count active sessions

        Args:
            bot_id: Optional bot ID filter

        Returns:
            Number of active sessions
        """
        stmt = select(func.count(Session.session_id)).where(
            Session.status == SessionStatus.ACTIVE.value
        )

        if bot_id:
            stmt = stmt.where(Session.bot_id == bot_id)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def increment_validation_attempts(
        self,
        session_id: UUID
    ) -> int:
        """
        Increment validation attempts counter

        Args:
            session_id: Session UUID

        Returns:
            New validation attempts count
        """
        from sqlalchemy import update
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(validation_attempts=Session.validation_attempts + 1)
            .returning(Session.validation_attempts)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def reset_validation_attempts(self, session_id: UUID) -> None:
        """
        Reset validation attempts to zero

        Args:
            session_id: Session UUID
        """
        from sqlalchemy import update
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(validation_attempts=0)
        )
        await self.session.execute(stmt)
