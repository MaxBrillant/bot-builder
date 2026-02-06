"""
Bot Service
Handles bot lifecycle and management operations using repository pattern
"""

from typing import Optional, List
from uuid import UUID
import secrets
import hmac
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot
from app.repositories.bot_repository import BotRepository
from app.utils.exceptions import BotNotFoundError, UnauthorizedError
from app.utils.constants import BotStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BotService:
    """Service for managing bots with explicit transaction control"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bot_repo = BotRepository(db)
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """
        Generate a secure webhook secret

        Returns:
            64-character URL-safe random string (48 bytes of entropy)
        """
        return secrets.token_urlsafe(48)
    
    async def create_bot(
        self,
        name: str,
        owner_user_id,
        description: Optional[str] = None
    ) -> Bot:
        """
        Create a new bot with auto-generated webhook secret
        
        Args:
            name: Bot display name
            owner_user_id: ID of the user who owns this bot (UUID or string)
            description: Optional bot description
            
        Returns:
            Created Bot object
        """
        bot = Bot(
            owner_user_id=owner_user_id,
            name=name,
            webhook_secret=self.generate_webhook_secret(),
            status=BotStatus.ACTIVE.value
        )
        
        if description:
            bot.description = description
        
        self.db.add(bot)
        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(f"Bot created: {bot.bot_id} (name: {bot.name})", owner_user_id=str(owner_user_id))

        return bot
    
    async def get_bot(
        self,
        bot_id: UUID,
        owner_user_id: Optional[UUID] = None,
        check_ownership: bool = True
    ) -> Bot:
        """
        Get bot by ID with optional ownership check

        Args:
            bot_id: Bot identifier
            owner_user_id: User ID to verify ownership (required if check_ownership=True)
            check_ownership: Whether to verify the user owns this bot

        Returns:
            Bot object

        Raises:
            BotNotFoundError: Bot not found
            UnauthorizedError: User doesn't own this bot
        """
        bot = await self.bot_repo.get_by_id(bot_id)

        if not bot:
            raise BotNotFoundError(
                message=f"Bot {bot_id} not found",
                error_code="BOT_NOT_FOUND",
                bot_id=str(bot_id)
            )

        if check_ownership and bot.owner_user_id != owner_user_id:
            raise UnauthorizedError(
                message="You don't have permission to access this bot",
                error_code="UNAUTHORIZED",
                bot_id=str(bot_id),
                user_id=str(owner_user_id)
            )

        return bot
    
    async def list_bots(
        self,
        owner_user_id: UUID,
        status: Optional[str] = None
    ) -> List[Bot]:
        """
        List all bots owned by a user with eager-loaded flows

        Args:
            owner_user_id: User ID
            status: Optional filter by status ('ACTIVE' or 'INACTIVE')

        Returns:
            List of Bot objects with flows eager-loaded (solves N+1 queries)
        """
        if status:
            return await self.bot_repo.get_active_bots(owner_user_id) if status == BotStatus.ACTIVE.value else []

        return await self.bot_repo.get_user_bots(owner_user_id)
    
    async def update_bot(
        self,
        bot_id: UUID,
        owner_user_id,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Bot:
        """
        Update bot details

        Args:
            bot_id: Bot identifier
            owner_user_id: User ID (for ownership check)
            name: New bot name
            description: New description
            status: New status ('ACTIVE' or 'INACTIVE')

        Returns:
            Updated Bot object

        Raises:
            NotFoundError: Bot not found
            UnauthorizedError: User doesn't own this bot
        """
        bot = await self.get_bot(bot_id, owner_user_id, check_ownership=True)
        
        if name is not None:
            bot.name = name
        if description is not None:
            bot.description = description
        if status is not None:
            bot.status = status
        
        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(f"Bot updated: {bot.bot_id} (name: {bot.name})", owner_user_id=str(owner_user_id))

        return bot

    async def delete_bot(
        self,
        bot_id: UUID,
        owner_user_id: UUID
    ) -> None:
        """
        Delete a bot (cascades to flows and sessions via FK constraints)

        Args:
            bot_id: Bot identifier
            owner_user_id: User ID (for ownership check)

        Raises:
            BotNotFoundError: Bot not found
            UnauthorizedError: User doesn't own this bot
        """
        bot = await self.get_bot(bot_id, owner_user_id, check_ownership=True)

        await self.bot_repo.delete(bot)
        await self.db.commit()

        logger.info(f"Bot deleted: {bot_id} (name: {bot.name})", owner_user_id=str(owner_user_id))
    
    async def regenerate_webhook_secret(
        self,
        bot_id: UUID,
        owner_user_id
    ) -> Bot:
        """
        Regenerate webhook secret for security
        
        Args:
            bot_id: Bot identifier
            owner_user_id: User ID (for ownership check)
            
        Returns:
            Updated Bot object with new webhook_secret
            
        Raises:
            NotFoundError: Bot not found
            UnauthorizedError: User doesn't own this bot
        """
        bot = await self.get_bot(bot_id, owner_user_id, check_ownership=True)
        
        bot.webhook_secret = self.generate_webhook_secret()
        
        await self.db.commit()
        await self.db.refresh(bot)

        logger.info(f"Webhook secret regenerated for bot: {bot.bot_id}", owner_user_id=str(owner_user_id))

        return bot
    
    async def verify_webhook_secret(
        self,
        bot_id: UUID,
        secret: str
    ) -> bool:
        """
        Verify webhook authentication using constant-time comparison

        Args:
            bot_id: Bot identifier
            secret: Webhook secret to verify

        Returns:
            True if secret matches, False otherwise

        Note:
            Uses hmac.compare_digest for timing-attack resistance.
            Always performs comparison even if bot not found to prevent timing attacks.
        """
        try:
            bot = await self.get_bot(bot_id, check_ownership=False)
            actual_secret = bot.webhook_secret
        except BotNotFoundError:
            # Use dummy secret for constant-time comparison
            actual_secret = "x" * 64

        # Always perform comparison to prevent timing attack
        return hmac.compare_digest(actual_secret, secret)
    
    async def set_bot_status(
        self,
        bot_id: UUID,
        owner_user_id,
        status: str
    ) -> Bot:
        """
        Activate or deactivate a bot

        Args:
            bot_id: Bot identifier
            owner_user_id: User ID (for ownership check)
            status: 'ACTIVE' or 'INACTIVE'

        Returns:
            Updated Bot object

        Raises:
            NotFoundError: Bot not found
            UnauthorizedError: User doesn't own this bot
        """
        return await self.update_bot(bot_id, owner_user_id, status=status)

    async def create_example_bot_for_user(self, user_id) -> None:
        """
        Create a "Getting Started" bot with example flows for a new user

        This is called automatically after user registration to provide
        ready-to-use examples demonstrating all bot capabilities.

        Args:
            user_id: UUID of the newly registered user

        Returns:
            None (errors are silently caught to avoid blocking registration)
        """
        try:
            # Import here to avoid circular dependency
            from app.services.flow_service import FlowService
            from app.utils.example_flows import get_all_example_flows

            # Create the example bot
            bot = await self.create_bot(
                name="Getting Started",
                owner_user_id=user_id,
                description="Example flows demonstrating bot capabilities"
            )

            logger.info(
                f"Created example bot for new user",
                user_id=str(user_id),
                bot_id=str(bot.bot_id)
            )

            # Create all example flows
            flow_service = FlowService(self.db)
            example_flows = get_all_example_flows()

            for flow_definition in example_flows:
                try:
                    await flow_service.create_flow(
                        flow_data=flow_definition,
                        bot_id=bot.bot_id
                    )
                except Exception as e:
                    # Continue creating other flows even if one fails
                    error_details = str(e)
                    validation_errors = None

                    # Extract validation errors from metadata (FlowValidationError stores errors there)
                    if hasattr(e, 'metadata') and isinstance(e.metadata, dict):
                        validation_errors = e.metadata.get('errors')

                    logger.error(
                        f"Failed to create example flow: {flow_definition.get('name', 'Unknown')}",
                        error=error_details,
                        error_type=type(e).__name__,
                        validation_errors=validation_errors,
                        user_id=str(user_id)
                    )
                    continue

            logger.info(
                f"Successfully created example bot with flows",
                user_id=str(user_id),
                bot_id=str(bot.bot_id),
                flow_count=len(example_flows)
            )

        except Exception as e:
            # Don't raise - we don't want registration to fail if example bot creation fails
            logger.error(
                f"Failed to create example bot for user",
                user_id=str(user_id),
                error=str(e)
            )