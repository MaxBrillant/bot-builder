"""
Flow Service
Handles flow CRUD operations with Redis caching using repository pattern
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.flow import Flow
from app.repositories.flow_repository import FlowRepository
from app.core.redis_manager import redis_manager
from app.core.flow_validator import FlowValidator
from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import FlowValidationError, FlowNotFoundError

logger = get_logger(__name__)


class FlowService:
    """Service for managing flows with Redis caching and explicit transaction control"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.flow_repo = FlowRepository(db)
        self.validator = FlowValidator(db)
    
    async def create_flow(
        self,
        flow_data: Dict[str, Any],
        bot_id: UUID
    ) -> Flow:
        """
        Create a new flow with validation and caching.

        Args:
            flow_data: Flow definition
            bot_id: Bot ID that owns the flow

        Returns:
            Created flow

        Raises:
            ValidationError: If flow validation fails or flow too large
        """
        # Validate flow size (prevent PostgreSQL JSONB issues)
        flow_json = json.dumps(flow_data, default=str)
        # Use actual UTF-8 byte size, not Python object overhead
        flow_size = len(flow_json.encode('utf-8'))

        if flow_size > settings.flow_constraints.max_flow_size:
            raise FlowValidationError(
                message=f"Flow definition too large ({flow_size} bytes). "
                        f"Maximum allowed: {settings.flow_constraints.max_flow_size} bytes",
                error_code="FLOW_TOO_LARGE",
                flow_size=flow_size,
                max_size=settings.flow_constraints.max_flow_size
            )

        # Validate flow structure
        validation_result = await self.validator.validate_flow(flow_data, bot_id)
        if not validation_result.is_valid():
            raise FlowValidationError(
                message="Flow validation failed",
                error_code="FLOW_VALIDATION_FAILED",
                errors=validation_result.errors
            )
        
        # Create flow model
        # Normalize trigger keywords to uppercase for case-insensitive matching
        trigger_keywords = [kw.strip().upper() for kw in flow_data.get("trigger_keywords", [])]
        
        flow = Flow(
            name=flow_data["name"],
            bot_id=bot_id,
            flow_definition=flow_data,
            trigger_keywords=trigger_keywords
        )
        
        try:
            flow = await self.flow_repo.add(flow)
            await self.db.commit()
            await self.db.refresh(flow)

            # Cache the flow
            await self._cache_flow(flow)

            # Cache trigger keywords
            await self._cache_trigger_keywords(flow)

            logger.info(f"Flow created: {flow.id} (name: {flow.name})", bot_id=str(bot_id))
            return flow

        except IntegrityError as e:
            await self.db.rollback()
            if "unique_flow_name_per_bot" in str(e) or "name" in str(e):
                raise FlowValidationError(
                    message=f"Flow name '{flow_data['name']}' already exists in this bot",
                    error_code="DUPLICATE_FLOW_NAME",
                    flow_name=flow_data['name'],
                    bot_id=str(bot_id)
                )
            raise
    
    async def get_flow(self, flow_id: UUID, bot_id: UUID) -> Optional[Flow]:
        """
        Get flow by UUID with caching.
        
        Args:
            flow_id: Flow UUID identifier
            bot_id: Bot ID that owns the flow
            
        Returns:
            Flow or None if not found
        """
        # Try cache first
        cached = await redis_manager.get_cached_flow(str(flow_id))
        if cached and cached.get("bot_id") == str(bot_id):
            logger.debug(f"Flow cache hit: {flow_id}")
            # Convert to Flow model with timestamps
            flow = Flow(
                id=UUID(cached["id"]),
                name=cached["name"],
                bot_id=UUID(cached["bot_id"]),
                flow_definition=cached["flow_definition"],
                trigger_keywords=cached.get("trigger_keywords", [])
            )
            # Restore timestamps from cache
            if cached.get("created_at"):
                flow.created_at = datetime.fromisoformat(cached["created_at"])
            if cached.get("updated_at"):
                flow.updated_at = datetime.fromisoformat(cached["updated_at"])
            return flow
        
        # Cache miss - query database using repository
        flow = await self.flow_repo.get_by_id_and_bot(flow_id, bot_id)

        if flow:
            # Cache for future requests
            await self._cache_flow(flow)

        return flow
    
    async def get_flow_by_id_only(self, flow_id: UUID) -> Optional[Flow]:
        """
        Get flow by UUID without bot check (for internal use).
        
        Args:
            flow_id: Flow UUID identifier
            
        Returns:
            Flow or None if not found
        """
        # Try cache first
        cached = await redis_manager.get_cached_flow(str(flow_id))
        if cached:
            flow = Flow(
                id=UUID(cached["id"]),
                name=cached["name"],
                bot_id=UUID(cached["bot_id"]),
                flow_definition=cached["flow_definition"],
                trigger_keywords=cached.get("trigger_keywords", [])
            )
            # Restore timestamps from cache
            if cached.get("created_at"):
                flow.created_at = datetime.fromisoformat(cached["created_at"])
            if cached.get("updated_at"):
                flow.updated_at = datetime.fromisoformat(cached["updated_at"])
            return flow
        
        # Cache miss - query database using repository
        flow = await self.flow_repo.get_by_id(flow_id)

        if flow:
            await self._cache_flow(flow)

        return flow
    
    async def list_flows(
        self,
        bot_id: UUID,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "desc"
    ) -> List[Flow]:
        """
        List flows for a bot

        Args:
            bot_id: Bot ID
            skip: Number of records to skip
            limit: Maximum records to return
            order_by: Sort order - "asc" for oldest first, "desc" for newest first (default: "desc")

        Returns:
            List of flows ordered by creation time
        """
        return await self.flow_repo.get_bot_flows(bot_id, offset=skip, limit=limit, order_by=order_by)

    async def count_flows(self, bot_id: UUID) -> int:
        """
        Count total flows for a bot

        Args:
            bot_id: Bot ID

        Returns:
            Total number of flows
        """
        return await self.flow_repo.count_bot_flows(bot_id)
    
    async def update_flow(
        self,
        flow_id: UUID,
        bot_id: UUID,
        flow_data: Dict[str, Any]
    ) -> Flow:
        """
        Update existing flow.
        
        Args:
            flow_id: Flow UUID identifier
            bot_id: Bot ID
            flow_data: Updated flow definition (may include new name)
            
        Returns:
            Updated flow
            
        Raises:
            NotFoundError: If flow not found
            ValidationError: If validation fails
        """
        # Get existing flow directly from database (bypass cache for updates)
        # Cache objects aren't attached to session and can't be refreshed
        flow = await self.flow_repo.get_by_id_and_bot(flow_id, bot_id)
        if not flow:
            raise FlowNotFoundError(
                message=f"Flow '{flow_id}' not found",
                error_code="FLOW_NOT_FOUND",
                flow_id=str(flow_id),
                bot_id=str(bot_id)
            )

        # Validate flow size (prevent PostgreSQL JSONB issues)
        flow_json = json.dumps(flow_data, default=str)
        # Use actual UTF-8 byte size, not Python object overhead
        flow_size = len(flow_json.encode('utf-8'))

        if flow_size > settings.flow_constraints.max_flow_size:
            raise FlowValidationError(
                message=f"Flow definition too large ({flow_size} bytes). "
                        f"Maximum allowed: {settings.flow_constraints.max_flow_size} bytes",
                error_code="FLOW_TOO_LARGE",
                flow_size=flow_size,
                max_size=settings.flow_constraints.max_flow_size
            )

        # Validate new flow data (pass current flow_id to exclude from duplicate checks)
        validation_result = await self.validator.validate_flow(
            flow_data,
            bot_id,
            current_flow_id=flow_id
        )
        if not validation_result.is_valid():
            raise FlowValidationError(
                message="Flow validation failed",
                error_code="FLOW_VALIDATION_FAILED",
                errors=validation_result.errors
            )
        
        # Get old keywords for cleanup
        old_keywords = flow.trigger_keywords or []
        old_flow_id_str = str(flow.id)
        
        # Normalize new keywords to uppercase for case-insensitive matching
        new_keywords = [kw.strip().upper() for kw in flow_data.get("trigger_keywords", [])]
        
        # Update flow (allow name change if provided)
        if "name" in flow_data:
            flow.name = flow_data["name"]
        flow.flow_definition = flow_data
        flow.trigger_keywords = new_keywords
        flow.updated_at = datetime.now()
        
        await self.db.commit()
        
        # Refresh flow to get updated values
        await self.db.refresh(flow)
        
        # Invalidate old cache (UUID string key)
        await redis_manager.invalidate_flow_cache(old_flow_id_str)
        
        # Remove old trigger keywords
        await redis_manager.invalidate_all_triggers_for_flow(old_flow_id_str, old_keywords, str(bot_id))
        
        # Cache updated flow
        await self._cache_flow(flow)
        
        # Cache new trigger keywords
        await self._cache_trigger_keywords(flow)
        
        logger.info(f"Flow updated: {flow.id} (name: {flow.name})", bot_id=str(bot_id))
        return flow
    
    async def delete_flow(self, flow_id: UUID, bot_id: UUID) -> bool:
        """
        Delete a flow

        Args:
            flow_id: Flow UUID identifier
            bot_id: Bot ID

        Returns:
            True if deleted, False if not found
        """
        # Get flow for trigger keywords
        flow = await self.get_flow(flow_id, bot_id)
        if not flow:
            return False

        flow_id_str = str(flow_id)

        # Delete from database using repository
        deleted = await self.flow_repo.delete_by_id_and_bot(flow_id, bot_id)
        if deleted:
            await self.db.commit()

        # Invalidate cache
        await redis_manager.invalidate_flow_cache(flow_id_str)

        # Remove trigger keywords
        if flow.trigger_keywords:
            await redis_manager.invalidate_all_triggers_for_flow(
                flow_id_str,
                flow.trigger_keywords,
                str(bot_id)
            )

        logger.info(f"Flow deleted: {flow_id} (name: {flow.name})", bot_id=str(bot_id))
        return deleted
    
    async def find_flow_by_keyword(self, keyword: str, bot_id: UUID) -> Optional[Flow]:
        """
        Find flow by trigger keyword within a specific bot

        Args:
            keyword: Trigger keyword
            bot_id: Bot ID to search within

        Returns:
            Flow or None if not found
        """
        # Try Redis first (bot-scoped) - returns UUID strings
        flow_id_strs = await redis_manager.get_flows_by_keyword(keyword, str(bot_id))

        if flow_id_strs:
            # Return first flow (sorted alphabetically for deterministic behavior)
            flow_id = UUID(flow_id_strs[0])
            flow = await self.get_flow(flow_id, bot_id)
            return flow

        # Fallback to database query using repository
        flow = await self.flow_repo.get_by_trigger_keyword(bot_id, keyword)

        if flow:
            # Cache for future lookups
            await self._cache_flow(flow)
            await self._cache_trigger_keywords(flow)

        return flow
    
    async def _cache_flow(self, flow: Flow):
        """Cache flow data in Redis using UUID as key"""
        if not redis_manager.is_connected():
            return
        
        flow_data = {
            "id": str(flow.id),
            "name": flow.name,
            "bot_id": str(flow.bot_id),
            "flow_definition": flow.flow_definition,
            "trigger_keywords": flow.trigger_keywords or [],
            "created_at": flow.created_at.isoformat() if flow.created_at else None,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None
        }
        
        await redis_manager.cache_flow(
            str(flow.id),  # Cache key is UUID string
            flow_data,
            ttl=settings.cache.flow_ttl
        )
    
    async def _cache_trigger_keywords(self, flow: Flow):
        """Cache trigger keyword mappings (bot-scoped) using UUID"""
        if not redis_manager.is_connected():
            return
        
        keywords = flow.trigger_keywords or []
        for keyword in keywords:
            await redis_manager.cache_trigger_keyword(keyword, str(flow.id), str(flow.bot_id))