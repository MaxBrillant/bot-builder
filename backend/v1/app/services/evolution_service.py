"""
Evolution API Service
HTTP client for Evolution API v2 operations with shared/managed instance
"""

from typing import Optional, Dict, Any, List
import httpx

from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class EvolutionAPIError(ExternalServiceError):
    """Evolution API specific error"""
    pass


class EvolutionAPIService:
    """
    Service for interacting with Evolution API v2.2.3

    Uses Evolution API v2.x with camelCase field names and nested webhook configuration.

    Key differences from v1:
    - Webhook config is nested under "webhook" object
    - Uses camelCase: webhookByEvents, base64 (not webhook_by_events, webhook_base64)
    - Health endpoint is "/" not "/health"
    - Instance response includes instanceId and token

    Uses global Evolution API configuration from settings.
    No per-bot API URL/key needed - much simpler!
    """

    def __init__(self, http_client: httpx.AsyncClient):
        """
        Initialize Evolution API service

        Args:
            http_client: Shared httpx AsyncClient for making requests
        """
        self.http_client = http_client
        self.api_url = str(settings.evolution_api.url).rstrip('/')
        self.api_key = settings.evolution_api.api_key
        self.logger = get_logger(__name__)

    async def create_instance(
        self,
        instance_name: str,
        integration: str = "WHATSAPP-BAILEYS",
        qrcode: bool = True,
        webhook_url: Optional[str] = None,
        webhook_by_events: bool = False,
        webhook_base64: bool = False,
        events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create new Evolution API v2.2.3 instance with optional webhook configuration

        Evolution API v2.2.3 returns QR codes immediately in the response AND supports
        webhook configuration in the create payload for automatic status updates.

        This implements the HYBRID approach verified through testing:
        - Get QR code immediately from response (no polling needed)
        - Configure webhooks for automatic CONNECTION_UPDATE and MESSAGES_UPSERT events
        - Best of both worlds: immediate UX + real-time updates

        Args:
            instance_name: Unique instance identifier (format: bot_{uuid_with_underscores})
            integration: Integration type (default: WHATSAPP-BAILEYS)
            qrcode: Whether to return QR code in response (default: True)
            webhook_url: Optional webhook URL to receive events (e.g., http://api:8000/evolution-webhooks/)
            webhook_by_events: Whether to append event names to webhook URL (default: False)
            webhook_base64: Whether to include base64 QR in webhook payloads (default: False)
            events: Optional list of events (e.g., ["QRCODE_UPDATED", "CONNECTION_UPDATE", "MESSAGES_UPSERT"])

        Returns:
            Instance details from Evolution API including:
            - instance: {instanceName, instanceId, integration, status, ...}
            - hash: Instance token for authentication
            - webhook: Webhook configuration (if provided)
            - qrcode: {base64: "data:image/png;base64,...", code: "2@...", count: N}

        Raises:
            EvolutionAPIError: If instance creation fails

        Note:
            Evolution API v2.2.3 does NOT support custom webhook headers.
            Webhook authentication must rely on network isolation.
        """
        url = f"{self.api_url}/instance/create"
        headers = {"apikey": self.api_key}
        payload = {
            "instanceName": instance_name,
            "integration": integration,
            "qrcode": qrcode
        }

        # Add webhook configuration if provided (v2.2.3 uses NESTED webhook object)
        # Webhook config goes NESTED under "webhook" object with camelCase fields
        if webhook_url and events:
            payload["webhook"] = {
                "url": webhook_url,
                "byEvents": webhook_by_events,  # v2 uses camelCase
                "base64": webhook_base64,        # v2 uses camelCase
                "events": events
            }
            # NOTE: v2.2.3 does NOT support custom webhook headers

        try:
            self.logger.info(f"Creating Evolution API instance: {instance_name}")
            self.logger.info(f"Request URL: {url}")
            self.logger.info(f"Request payload: {payload}")
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Create instance response: {data}")
            self.logger.info(f"Successfully created instance: {instance_name}")
            return data
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.json()
                self.logger.error(f"Evolution API error response: {error_body}")
            except:
                error_body = e.response.text
                self.logger.error(f"Evolution API error response (text): {error_body}")
            error_msg = f"Failed to create instance {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error creating instance {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    async def configure_webhook(
        self,
        instance_name: str,
        webhook_url: str,
        events: List[str],
        webhook_by_events: bool = False,
        webhook_base64: bool = False
    ) -> Dict[str, Any]:
        """
        Configure webhook for an Evolution API v2.2.3 instance

        This is the standard way to receive QR codes and other events from Evolution API.
        QR codes are delivered via the QRCODE_UPDATED webhook event, not via REST API.

        Uses v2.x camelCase field names.

        Args:
            instance_name: Instance identifier
            webhook_url: URL to receive webhook POSTs
            events: List of events to listen to (e.g., ["QRCODE_UPDATED", "CONNECTION_UPDATE"])
            webhook_by_events: Whether to append event names to webhook URL (default: False)
            webhook_base64: Whether to include base64 QR in webhook payloads (default: False)

        Returns:
            Webhook configuration response

        Raises:
            EvolutionAPIError: If webhook configuration fails

        Example:
            await evolution_service.configure_webhook(
                instance_name="bot_123",
                webhook_url="http://api:8000/evolution-webhooks/",
                events=["QRCODE_UPDATED", "CONNECTION_UPDATE", "MESSAGES_UPSERT"]
            )
        """
        url = f"{self.api_url}/webhook/instance"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        # v2.2.3 uses camelCase field names
        payload = {
            "instanceName": instance_name,
            "enabled": True,
            "url": webhook_url,
            "webhookByEvents": webhook_by_events,  # v2 uses camelCase
            "base64": webhook_base64,              # v2 uses camelCase
            "events": events
        }

        try:
            self.logger.info(f"Configuring webhook for instance: {instance_name}")
            self.logger.info(f"Webhook URL: {webhook_url}")
            self.logger.info(f"Webhook events: {events}")
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Webhook configured successfully for {instance_name}")
            return data
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.json()
                self.logger.error(f"Evolution API error response: {error_body}")
            except:
                error_body = e.response.text
                self.logger.error(f"Evolution API error response (text): {error_body}")
            error_msg = f"Failed to configure webhook for {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error configuring webhook for {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    async def get_connection_state(self, instance_name: str) -> Dict[str, Any]:
        """
        Check connection status of an instance

        Args:
            instance_name: Instance identifier

        Returns:
            Dictionary with state ("open", "close", "connecting") and instance details

        Raises:
            EvolutionAPIError: If status check fails
        """
        url = f"{self.api_url}/instance/connectionState/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            self.logger.debug(f"Checking connection state for instance: {instance_name}")
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.debug(f"Connection state for {instance_name}: {data.get('state')}")
            return data
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to get connection state for {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error checking connection state for {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    async def send_text_message(
        self,
        instance_name: str,
        phone_number: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Send text message to WhatsApp user

        Args:
            instance_name: Instance identifier
            phone_number: Phone number (will be normalized automatically)
            text: Message text to send

        Returns:
            Response from Evolution API

        Raises:
            EvolutionAPIError: If message sending fails
        """
        url = f"{self.api_url}/message/sendText/{instance_name}"
        headers = {"apikey": self.api_key}

        # Normalize phone number (remove + and @s.whatsapp.net suffix)
        normalized_number = self._normalize_phone_number(phone_number)

        payload = {
            "number": normalized_number,
            "text": text
        }

        try:
            self.logger.info(f"Sending message to {normalized_number} via {instance_name}")
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Successfully sent message to {normalized_number}")
            return data
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to send message via {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error sending message via {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    async def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Logout WhatsApp connection (keeps instance)

        Args:
            instance_name: Instance identifier

        Returns:
            Response from Evolution API

        Raises:
            EvolutionAPIError: If logout fails
        """
        url = f"{self.api_url}/instance/logout/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            self.logger.info(f"Logging out instance: {instance_name}")
            response = await self.http_client.delete(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Successfully logged out instance: {instance_name}")
            return data
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to logout instance {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error logging out instance {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    async def delete_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Delete Evolution API instance completely

        Args:
            instance_name: Instance identifier

        Returns:
            Response from Evolution API

        Raises:
            EvolutionAPIError: If deletion fails
        """
        url = f"{self.api_url}/instance/delete/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            self.logger.info(f"Deleting instance: {instance_name}")
            response = await self.http_client.delete(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Successfully deleted instance: {instance_name}")
            return data
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to delete instance {instance_name}: HTTP {e.response.status_code}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error deleting instance {instance_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise EvolutionAPIError(error_msg) from e

    def _normalize_phone_number(self, phone: str) -> str:
        """
        Normalize phone number for Evolution API

        Removes + prefix and @s.whatsapp.net suffix if present

        Args:
            phone: Phone number in various formats

        Returns:
            Normalized phone number (just digits)

        Examples:
            "+5511999999999" -> "5511999999999"
            "5511999999999@s.whatsapp.net" -> "5511999999999"
            "5511999999999" -> "5511999999999"
        """
        # Remove + prefix
        normalized = phone.lstrip('+')

        # Remove @s.whatsapp.net suffix if present
        if '@' in normalized:
            normalized = normalized.split('@')[0]

        return normalized
