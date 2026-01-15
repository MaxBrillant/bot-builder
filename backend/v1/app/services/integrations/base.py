"""
Base Integration Service Interface

All platform integrations must implement this interface to ensure
consistent behavior across different messaging platforms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

from app.utils.constants import IntegrationPlatform


class IntegrationService(ABC):
    """
    Abstract base class for platform integrations

    Design Principles:
    - Each platform (WhatsApp, Telegram, Slack) implements this interface
    - Core system interacts only with this interface, not concrete implementations
    - Platform-specific details encapsulated within implementations
    """

    @property
    @abstractmethod
    def platform(self) -> IntegrationPlatform:
        """
        Return the platform enum this integration handles

        Returns:
            IntegrationPlatform enum value
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        bot_id: UUID,
        channel_user_id: str,
        message_text: str
    ) -> bool:
        """
        Send message to user on this platform

        Args:
            bot_id: Bot identifier
            channel_user_id: Platform-specific user identifier
                            (e.g., phone number for WhatsApp, user_id for Telegram)
            message_text: Message content to send

        Returns:
            True if message sent successfully, False otherwise

        Note:
            Implementation should handle:
            - Retrieving integration config from database
            - Checking connection status
            - Platform-specific API calls
            - Error handling and logging
        """
        pass

    @abstractmethod
    async def get_connection_status(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Get current connection status for bot on this platform

        Args:
            bot_id: Bot identifier

        Returns:
            Status dictionary with minimum keys:
            {
                "status": str,  # connected, disconnected, connecting, error, not_configured
                "platform": str,  # Platform name
                "connected_at": str | None,  # ISO timestamp if connected
                # Additional platform-specific fields as needed
            }
        """
        pass

    @abstractmethod
    def normalize_webhook_message(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Transform platform-specific webhook payload to normalized format

        This is the KEY method for maintaining platform-agnostic design.
        Each platform receives webhooks in different formats - this method
        translates them to the standard format the core system expects.

        Args:
            raw_data: Complete platform-specific webhook payload

        Returns:
            Normalized message dict with exact keys:
            {
                "channel": str,  # Platform identifier (whatsapp, telegram, etc.)
                "channel_user_id": str,  # Platform-specific user ID
                "message_text": str  # Message content
            }

            Or None if message should be ignored (e.g., bot's own message,
            status update, unsupported message type)

        Examples:
            WhatsApp: Transforms Evolution API format to normalized format
            Telegram: Transforms Bot API format to normalized format
            Slack: Transforms Events API format to normalized format
        """
        pass

    # Optional methods that can be overridden

    async def connect(self, bot_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize connection for bot on this platform (optional)

        Args:
            bot_id: Bot identifier
            config: Platform-specific configuration

        Returns:
            Result dict with status and details

        Note:
            Not all platforms require explicit connection initialization.
            Default implementation returns not_implemented.
        """
        return {
            "status": "not_implemented",
            "message": f"Connect not implemented for {self.platform.value}"
        }

    async def disconnect(self, bot_id: UUID) -> bool:
        """
        Disconnect bot from this platform (optional)

        Args:
            bot_id: Bot identifier

        Returns:
            True if disconnected successfully

        Note:
            Not all platforms require explicit disconnection.
            Default implementation returns True.
        """
        return True

    async def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate platform-specific configuration (optional)

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_message)

        Note:
            Override to implement platform-specific validation.
            Default implementation accepts all configs.
        """
        return True, None
