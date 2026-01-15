"""
WhatsApp Integration via Evolution API v2

This integration handles all WhatsApp-specific logic:
- Message sending via Evolution API
- Webhook payload normalization
- Connection status tracking
"""

from typing import Dict, Any, Optional
from uuid import UUID
import httpx

from app.services.integrations.base import IntegrationService
from app.services.evolution_service import EvolutionAPIService, EvolutionAPIError
from app.repositories.bot_integration_repository import BotIntegrationRepository
from app.utils.constants import IntegrationPlatform, IntegrationStatus
from app.utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class WhatsAppIntegration(IntegrationService):
    """WhatsApp integration via Evolution API"""

    def __init__(self, db: AsyncSession, http_client: httpx.AsyncClient):
        """
        Initialize WhatsApp integration

        Args:
            db: Database session for accessing integrations
            http_client: HTTP client for Evolution API calls
        """
        self.db = db
        self.http_client = http_client
        self.evolution = EvolutionAPIService(http_client)
        self.repo = BotIntegrationRepository(db)

    @property
    def platform(self) -> IntegrationPlatform:
        """Return WhatsApp platform enum"""
        return IntegrationPlatform.WHATSAPP

    async def send_message(
        self,
        bot_id: UUID,
        channel_user_id: str,
        message_text: str
    ) -> bool:
        """
        Send WhatsApp message via Evolution API

        Flow:
        1. Retrieve bot's WhatsApp integration from database
        2. Check if integration is connected
        3. Extract Evolution API instance name from config
        4. Send message via Evolution API
        5. Return success/failure
        """
        try:
            # Get WhatsApp integration config
            integration = await self.repo.get_by_bot_and_platform(bot_id, self.platform)

            if not integration:
                logger.warning(f"No WhatsApp integration for bot {bot_id}")
                return False

            if integration.status != IntegrationStatus.CONNECTED.value:
                logger.warning(
                    f"WhatsApp not connected for bot {bot_id}, status: {integration.status}"
                )
                return False

            # Extract instance name from config
            instance_name = integration.config.get('instance_name')
            if not instance_name:
                logger.error(f"Missing instance_name in WhatsApp config for bot {bot_id}")
                return False

            # Send via Evolution API
            await self.evolution.send_text_message(
                instance_name=instance_name,
                phone_number=channel_user_id,
                text=message_text
            )

            logger.info(
                f"WhatsApp message sent successfully",
                bot_id=str(bot_id),
                user=channel_user_id[:8] + "..."  # Log partial for privacy
            )
            return True

        except EvolutionAPIError as e:
            logger.error(
                f"Evolution API error sending message: {str(e)}",
                bot_id=str(bot_id)
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending WhatsApp message: {str(e)}",
                bot_id=str(bot_id),
                exc_info=True
            )
            return False

    async def get_connection_status(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Get WhatsApp connection status for bot

        Returns status dict with WhatsApp-specific fields
        """
        integration = await self.repo.get_by_bot_and_platform(bot_id, self.platform)

        if not integration:
            return {
                "status": "not_configured",
                "platform": self.platform.value,
                "message": "WhatsApp integration not configured"
            }

        return {
            "status": integration.status,
            "platform": self.platform.value,
            "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
            "phone_number": integration.config.get('phone_number'),
            "instance_name": integration.config.get('instance_name'),
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None
        }

    def normalize_webhook_message(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Transform Evolution API webhook to normalized format

        Evolution API Webhook Format (messages.upsert event):
        {
            "event": "messages.upsert",
            "instance": "bot_abc_instance",
            "data": {
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "fromMe": false,
                    "id": "message_id"
                },
                "message": {
                    "conversation": "Hello bot!"
                },
                "messageType": "conversation",
                "pushName": "User Name"
            }
        }

        Normalized Format:
        {
            "channel": "whatsapp",
            "channel_user_id": "5511999999999",
            "message_text": "Hello bot!"
        }
        """
        event = raw_data.get("event")

        # Only process new message events
        if event != "messages.upsert":
            logger.debug(f"Ignoring non-message event: {event}")
            return None

        data = raw_data.get("data", {})
        key = data.get("key", {})
        message_obj = data.get("message", {})

        # Ignore bot's own messages (fromMe = true)
        if key.get("fromMe", False):
            logger.debug("Ignoring bot's own message")
            return None

        # Extract phone number from remoteJid
        remote_jid = key.get("remoteJid", "")
        if not remote_jid:
            logger.warning("Missing remoteJid in webhook data")
            return None

        # Remove WhatsApp suffix to get clean phone number
        # Example: "5511999999999@s.whatsapp.net" -> "5511999999999"
        channel_user_id = remote_jid.split('@')[0]

        # Extract message text from various message types
        message_text = self._extract_message_text(message_obj, data.get("messageType"))

        if not message_text:
            logger.debug("Could not extract message text from webhook")
            return None

        return {
            "channel": self.platform.value,
            "channel_user_id": channel_user_id,
            "message_text": message_text
        }

    def _extract_message_text(self, message_obj: Dict, message_type: str) -> Optional[str]:
        """
        Extract text from different WhatsApp message types

        WhatsApp supports various message types with different structures.
        This method handles the most common types and provides fallbacks.

        Args:
            message_obj: The 'message' object from webhook
            message_type: Message type identifier

        Returns:
            Extracted text or placeholder for non-text messages
        """
        # Simple text message
        if "conversation" in message_obj:
            return message_obj["conversation"]

        # Extended text message (with formatting, links, mentions)
        if "extendedTextMessage" in message_obj:
            return message_obj["extendedTextMessage"].get("text")

        # Image with optional caption
        if "imageMessage" in message_obj:
            caption = message_obj["imageMessage"].get("caption")
            return caption if caption else "[Image]"

        # Video with optional caption
        if "videoMessage" in message_obj:
            caption = message_obj["videoMessage"].get("caption")
            return caption if caption else "[Video]"

        # Document with optional caption
        if "documentMessage" in message_obj:
            caption = message_obj["documentMessage"].get("caption")
            return caption if caption else "[Document]"

        # Audio message
        if "audioMessage" in message_obj:
            return "[Audio]"

        # Voice message
        if "audioMessage" in message_obj and message_obj["audioMessage"].get("ptt"):
            return "[Voice Note]"

        # Sticker
        if "stickerMessage" in message_obj:
            return "[Sticker]"

        # Location
        if "locationMessage" in message_obj:
            return "[Location]"

        # Contact
        if "contactMessage" in message_obj:
            return "[Contact]"

        # Unsupported or unknown type
        if message_type:
            logger.debug(f"Unsupported WhatsApp message type: {message_type}")
            return f"[Unsupported message type: {message_type}]"

        return None

    async def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate WhatsApp integration configuration

        Required fields:
        - instance_name: Evolution API instance identifier

        Optional fields:
        - phone_number: WhatsApp phone number (set after connection)
        """
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"

        instance_name = config.get('instance_name')
        if not instance_name:
            return False, "instance_name is required in config"

        if not isinstance(instance_name, str):
            return False, "instance_name must be a string"

        if len(instance_name) < 3:
            return False, "instance_name must be at least 3 characters"

        # Instance name format validation (if needed)
        # Evolution API typically uses: bot_{uuid_with_underscores}

        return True, None
