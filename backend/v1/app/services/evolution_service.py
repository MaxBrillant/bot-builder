"""
Evolution API Service
HTTP client for Evolution API v2.2.3 operations
"""

from typing import Optional, Dict, Any, List
import httpx

from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import ExternalServiceError


class EvolutionAPIError(ExternalServiceError):
    """Evolution API specific error"""
    pass


class EvolutionAPIService:
    """
    Service for interacting with Evolution API v2.2.3

    Key v2.x differences from v1:
    - Webhook config is nested under "webhook" object
    - Uses camelCase field names
    - QR code returned immediately in create response
    """

    def __init__(self, http_client: httpx.AsyncClient):
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
        """Create Evolution API instance with optional webhook configuration."""
        url = f"{self.api_url}/instance/create"
        headers = {"apikey": self.api_key}
        payload = {
            "instanceName": instance_name,
            "integration": integration,
            "qrcode": qrcode
        }

        if webhook_url and events:
            payload["webhook"] = {
                "url": webhook_url,
                "byEvents": webhook_by_events,
                "base64": webhook_base64,
                "events": events
            }

        try:
            self.logger.info(f"Creating instance: {instance_name}")
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._log_http_error(e)
            raise EvolutionAPIError(f"Failed to create instance {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error creating instance {instance_name}: {e}") from e

    async def fetch_instance(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """Check if instance exists. Returns instance details or None."""
        url = f"{self.api_url}/instance/fetchInstances"
        headers = {"apikey": self.api_key}
        params = {"instanceName": instance_name}

        try:
            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data[0] if isinstance(data, list) and data else None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            self._log_http_error(e)
            raise EvolutionAPIError(f"Failed to fetch instance {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error fetching instance {instance_name}: {e}") from e

    async def force_delete_instance(self, instance_name: str) -> bool:
        """
        Force delete an instance (logout + delete).
        Returns True after attempt (Evolution API may process async).
        """
        try:
            instance = await self.fetch_instance(instance_name)
        except EvolutionAPIError as e:
            self.logger.warning(f"Could not check if {instance_name} exists, skipping cleanup: {e}")
            return True

        if not instance:
            return True

        try:
            await self.logout_instance(instance_name)
        except EvolutionAPIError as e:
            self.logger.warning(f"Could not logout {instance_name}: {e}")

        try:
            await self.delete_instance(instance_name)
        except EvolutionAPIError as e:
            self.logger.warning(f"Could not delete {instance_name}: {e}")

        return True

    async def get_connection_state(self, instance_name: str) -> Dict[str, Any]:
        """Get connection status (open, close, connecting)."""
        url = f"{self.api_url}/instance/connectionState/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise EvolutionAPIError(f"Failed to get state for {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error getting state for {instance_name}: {e}") from e

    async def send_text_message(self, instance_name: str, phone_number: str, text: str) -> Dict[str, Any]:
        """Send text message to WhatsApp user."""
        url = f"{self.api_url}/message/sendText/{instance_name}"
        headers = {"apikey": self.api_key}
        payload = {
            "number": self._normalize_phone_number(phone_number),
            "text": text
        }

        try:
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._log_http_error(e)
            raise EvolutionAPIError(f"Failed to send message via {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error sending message via {instance_name}: {e}") from e

    async def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """Logout WhatsApp connection (keeps instance)."""
        url = f"{self.api_url}/instance/logout/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            response = await self.http_client.delete(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise EvolutionAPIError(f"Failed to logout {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error logging out {instance_name}: {e}") from e

    async def delete_instance(self, instance_name: str) -> Dict[str, Any]:
        """Delete Evolution API instance completely."""
        url = f"{self.api_url}/instance/delete/{instance_name}"
        headers = {"apikey": self.api_key}

        try:
            response = await self.http_client.delete(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise EvolutionAPIError(f"Failed to delete {instance_name}: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise EvolutionAPIError(f"Network error deleting {instance_name}: {e}") from e

    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number (remove + and @s.whatsapp.net)."""
        normalized = phone.lstrip('+')
        if '@' in normalized:
            normalized = normalized.split('@')[0]
        return normalized

    def _log_http_error(self, e: httpx.HTTPStatusError) -> None:
        """Log HTTP error response body for debugging."""
        try:
            self.logger.error(f"Evolution API error: {e.response.json()}")
        except Exception:
            self.logger.error(f"Evolution API error: {e.response.text}")
