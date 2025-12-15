"""
Base repository with common query patterns

Provides generic CRUD operations for all repositories
"""

from typing import TypeVar, Generic, Optional, List
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Base repository with shared CRUD methods

    All specific repositories inherit from this class and add
    domain-specific query methods.
    """

    def __init__(self, session: AsyncSession, model_class):
        """
        Initialize repository

        Args:
            session: SQLAlchemy async session
            model_class: Model class for this repository
        """
        self.session = session
        self.model = model_class

    async def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get entity by ID

        Args:
            id: Entity UUID

        Returns:
            Entity or None if not found
        """
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        """
        Add entity to session (does NOT commit)

        Args:
            entity: Entity to add

        Returns:
            The added entity
        """
        self.session.add(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """
        Delete entity from session (does NOT commit)

        Args:
            entity: Entity to delete
        """
        await self.session.delete(entity)

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete entity by ID (does NOT commit)

        Args:
            id: Entity UUID

        Returns:
            True if entity was deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """
        Check if entity exists

        Args:
            id: Entity UUID

        Returns:
            True if entity exists
        """
        entity = await self.get_by_id(id)
        return entity is not None
