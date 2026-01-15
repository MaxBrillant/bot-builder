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
            32-character random hex string
        """
        return secrets.token_hex(32)
    
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