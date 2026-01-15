"""
Integration Manager

Central registry and router for all platform integrations.
Provides unified interface for core system to interact with any platform.
"""

from typing import Dict, Optional
from uuid import UUID
import httpx

from app.services.integrations.base import IntegrationService
from app.services.integrations.whatsapp import WhatsAppIntegration
from app.utils.constants import IntegrationPlatform
from app.utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class IntegrationManager:
    """
    Central manager for platform integrations

    Responsibilities:
    1. Register all available platform integrations
    2. Route operations to appropriate platform
    3. Provide unified interface for core system
    4. Maintain registry of supported platforms

    Design Pattern: Registry + Strategy Pattern
    - Registry: Maps platforms to their implementations
    - Strategy: Core system uses same interface for all platforms
    """

    def __init__(self, db: AsyncSession, http_client: httpx.AsyncClient):
        """
        Initialize integration manager

        Args:
            db: Database session (passed to integrations)
            http_client: HTTP client (passed to integrations)
        """
        self.db = db
        self.http_client = http_client
        self._integrations: Dict[IntegrationPlatform, IntegrationService] = {}

        # Auto-register all available integrations
        self._register_integrations()

    def _register_integrations(self):
        """
        Register all available platform integrations

        Add new platforms here as they're implemented:
        1. Create integration class implementing IntegrationService
        2. Instantiate and register here
        3. Add to IntegrationPlatform enum
        """
        # WhatsApp via Evolution API
        whatsapp = WhatsAppIntegration(self.db, self.http_client)
        self._integrations[whatsapp.platform] = whatsapp

        # Future platforms:
        # telegram = TelegramIntegration(self.db, self.http_client)
        # self._integrations[telegram.platform] = telegram

        # slack = SlackIntegration(self.db, self.http_client)
        # self._integrations[slack.platform] = slack

        registered_platforms = [p.value for p in self._integrations.keys()]
        logger.info(f"IntegrationManager initialized with {len(self._integrations)} platforms: {registered_platforms}")

    def get_integration(self, platform: IntegrationPlatform) -> Optional[IntegrationService]:
        """
        Get integration service for specific platform

        Args:
            platform: Platform enum

        Returns:
            IntegrationService implementation or None if not registered
        """
        integration = self._integrations.get(platform)

        if not integration:
            logger.warning(f"No integration registered for platform: {platform.value}")

        return integration

    def get_available_platforms(self) -> list[IntegrationPlatform]:
        """
        Get list of all registered platform enums

        Returns:
            List of IntegrationPlatform enums
        """
        return list(self._integrations.keys())

    def is_platform_supported(self, platform: IntegrationPlatform) -> bool:
        """Check if platform is supported"""
        return platform in self._integrations

    async def send_message(
        self,
        platform: IntegrationPlatform,
        bot_id: UUID,
        channel_user_id: str,
        message_text: str
    ) -> bool:
        """
        Send message via specific platform integration

        This is the main method used by core system to send responses
        back to users after processing their messages.

        Args:
            platform: Platform enum (whatsapp, telegram, etc.)
            bot_id: Bot identifier
            channel_user_id: Platform-specific user ID
            message_text: Message content to send

        Returns:
            True if message sent successfully, False otherwise

        Example:
            await manager.send_message(
                IntegrationPlatform.WHATSAPP,
                bot_id=uuid.UUID("..."),
                channel_user_id="+5511999999999",
                message_text="Hello from bot!"
            )
        """
        integration = self.get_integration(platform)

        if not integration:
            logger.error(f"Cannot send message - platform not supported: {platform.value}")
            return False

        return await integration.send_message(bot_id, channel_user_id, message_text)

    def normalize_webhook(
        self,
        platform: IntegrationPlatform,
        raw_data: Dict
    ) -> Optional[Dict[str, str]]:
        """
        Normalize platform-specific webhook to standard format

        This is the KEY method for maintaining platform-agnostic design.
        Integration layer calls this to transform platform webhooks before
        sending to core /webhook/{bot_id} endpoint.

        Args:
            platform: Platform enum
            raw_data: Complete platform-specific webhook payload

        Returns:
            Normalized message dict or None if should be ignored

        Example:
            # WhatsApp webhook received
            raw_whatsapp_data = {...}  # Evolution API format

            # Normalize to standard format
            normalized = manager.normalize_webhook(
                IntegrationPlatform.WHATSAPP,
                raw_whatsapp_data
            )

            if normalized:
                # Send to core webhook
                response = await core_webhook(bot_id, normalized)
                # Send response back via platform
                await manager.send_message(...)
        """
        integration = self.get_integration(platform)

        if not integration:
            logger.error(f"Cannot normalize webhook - platform not supported: {platform.value}")
            return None

        return integration.normalize_webhook_message(raw_data)

    async def get_connection_status(
        self,
        platform: IntegrationPlatform,
        bot_id: UUID
    ) -> Dict[str, str]:
        """
        Get connection status for bot on specific platform

        Args:
            platform: Platform enum
            bot_id: Bot identifier

        Returns:
            Status dict with platform-specific details
        """
        integration = self.get_integration(platform)

        if not integration:
            return {
                "status": "unsupported",
                "platform": platform.value,
                "message": f"Platform {platform.value} not supported"
            }

        return await integration.get_connection_status(bot_id)

    async def get_all_statuses(self, bot_id: UUID) -> Dict[str, Dict]:
        """
        Get connection status for bot across all platforms

        Args:
            bot_id: Bot identifier

        Returns:
            Dict mapping platform names to status dicts

        Example:
            {
                "whatsapp": {"status": "connected", ...},
                "telegram": {"status": "not_configured", ...},
                "slack": {"status": "not_configured", ...}
            }
        """
        statuses = {}

        for platform in self._integrations.keys():
            status = await self.get_connection_status(platform, bot_id)
            statuses[platform.value] = status

        return statuses
