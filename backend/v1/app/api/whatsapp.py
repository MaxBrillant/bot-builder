"""
WhatsApp Management API
Endpoints for connecting and managing WhatsApp integrations via Evolution API v2.2.3
"""

import asyncio
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.bot_integration import BotIntegration
from app.services.bot_service import BotService
from app.services.evolution_service import EvolutionAPIService, EvolutionAPIError
from app.repositories.bot_integration_repository import BotIntegrationRepository
from app.schemas.whatsapp_schema import WhatsAppStatusResponse
from app.core.engine import get_http_client
from app.config import settings
from app.utils.exceptions import NotFoundError, UnauthorizedError
from app.utils.constants import IntegrationPlatform, IntegrationStatus
from app.utils.logger import get_logger
from app.utils.responses import (
    not_found,
    forbidden,
    service_unavailable,
    bad_gateway,
    internal_server_error
)

logger = get_logger(__name__)
router = APIRouter(prefix="/bots", tags=["whatsapp"])

# Webhook events to subscribe to
WEBHOOK_EVENTS = ["QRCODE_UPDATED", "CONNECTION_UPDATE", "MESSAGES_UPSERT"]


async def get_or_create_whatsapp_integration(db: AsyncSession, bot_id: UUID) -> BotIntegration:
    """Get or create WhatsApp integration for a bot."""
    repo = BotIntegrationRepository(db)
    integration = await repo.get_by_bot_and_platform(bot_id, IntegrationPlatform.WHATSAPP)

    if not integration:
        integration = BotIntegration(
            bot_id=bot_id,
            platform=IntegrationPlatform.WHATSAPP.value,
            config={},
            status=IntegrationStatus.DISCONNECTED.value
        )
        db.add(integration)
        await db.commit()
        await db.refresh(integration)
        logger.info(f"Created new WhatsApp integration for bot {bot_id}")

    return integration


async def verify_bot_ownership(db: AsyncSession, bot_id: UUID, user_id: UUID) -> None:
    """Verify the user owns the bot. Raises HTTPException if not."""
    bot_service = BotService(db)
    try:
        await bot_service.get_bot(bot_id=bot_id, owner_user_id=user_id, check_ownership=True)
    except NotFoundError:
        raise not_found("Bot not found")
    except UnauthorizedError:
        raise forbidden("Not authorized to access this bot")


async def create_evolution_instance(
    evolution_service: EvolutionAPIService,
    instance_name: str,
    webhook_url: str
) -> dict:
    """
    Create Evolution API instance with retry logic.
    Returns instance response with QR code.
    """
    for attempt in range(2):
        try:
            response = await evolution_service.create_instance(
                instance_name=instance_name,
                integration="WHATSAPP-BAILEYS",
                qrcode=True,
                webhook_url=webhook_url,
                webhook_by_events=False,
                webhook_base64=False,
                events=WEBHOOK_EVENTS
            )
            logger.info(f"Instance created: {instance_name}")
            return response
        except EvolutionAPIError as e:
            if "403" in str(e) and attempt == 0:
                logger.warning(f"Instance creation failed (403), retrying: {e}")
                await asyncio.sleep(1)
                await evolution_service.force_delete_instance(instance_name)
                await asyncio.sleep(0.5)
                continue
            raise

    raise EvolutionAPIError(f"Failed to create instance {instance_name} after retries")


def update_integration_config(integration: BotIntegration, updates: dict, removals: list = None) -> None:
    """Update integration config (must reassign for SQLAlchemy to detect JSONB changes)."""
    config = integration.config.copy() if integration.config else {}
    for key, value in updates.items():
        config[key] = value
    for key in (removals or []):
        config.pop(key, None)
    integration.config = config


@router.post("/{bot_id}/whatsapp/connect", response_model=WhatsAppStatusResponse)
async def connect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize WhatsApp connection. Returns QR code immediately.

    The QR code is returned in the response - no polling needed.
    Poll GET /status to detect when user scans the QR code.
    """
    if not settings.evolution_api.enabled:
        raise service_unavailable("WhatsApp integration is currently disabled")

    await verify_bot_ownership(db, bot_id, current_user.user_id)
    integration = await get_or_create_whatsapp_integration(db, bot_id)

    # Already connected
    if integration.status == IntegrationStatus.CONNECTED.value:
        return WhatsAppStatusResponse(
            status=IntegrationStatus.CONNECTED.value,
            instance_name=integration.config.get('instance_name'),
            phone_number=integration.config.get('phone_number'),
            connected_at=integration.connected_at,
            message="Already connected. Disconnect first to reconnect."
        )

    # Already connecting
    if integration.status == IntegrationStatus.CONNECTING.value and integration.config.get('instance_name'):
        return WhatsAppStatusResponse(
            status=IntegrationStatus.CONNECTING.value,
            instance_name=integration.config.get('instance_name'),
            message="Connection in progress. Use /reconnect to get a new QR code."
        )

    instance_name = f"bot_{str(bot_id).replace('-', '_')}"
    webhook_url = f"{settings.evolution_api.webhook_base_url}/evolution-webhooks"

    try:
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # Clean up any existing instance
        await evolution_service.force_delete_instance(instance_name)

        # Create new instance
        instance_response = await create_evolution_instance(evolution_service, instance_name, webhook_url)

        # Extract QR code
        qr_data = instance_response.get("qrcode", {})
        qr_code = qr_data.get("base64") or qr_data.get("code")

        # Update integration
        update_integration_config(integration, {'instance_name': instance_name}, ['phone_number'])
        integration.status = IntegrationStatus.CONNECTING.value
        integration.connected_at = None
        await db.commit()

        return WhatsAppStatusResponse(
            status=IntegrationStatus.CONNECTING.value,
            instance_name=instance_name,
            qr_code=qr_code,
            message="Scan QR code with WhatsApp"
        )

    except EvolutionAPIError as e:
        logger.error(f"Evolution API error for bot {bot_id}: {e}")
        raise bad_gateway(f"Evolution API error: {e}")
    except Exception as e:
        logger.error(f"Error connecting WhatsApp for bot {bot_id}: {e}", exc_info=True)
        raise internal_server_error("Failed to connect")


@router.get("/{bot_id}/whatsapp/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get WhatsApp connection status with real-time verification.

    Always queries Evolution API for current status to ensure accuracy,
    especially after server restarts when webhooks might be missed.
    """
    await verify_bot_ownership(db, bot_id, current_user.user_id)
    integration = await get_or_create_whatsapp_integration(db, bot_id)

    instance_name = integration.config.get('instance_name')

    # If no instance configured, return disconnected
    if not instance_name:
        return WhatsAppStatusResponse(
            status=IntegrationStatus.DISCONNECTED.value,
            instance_name=None,
            phone_number=None,
            connected_at=None
        )

    # Query Evolution API for real-time status
    try:
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # Get connection state from Evolution API
        state_response = await evolution_service.get_connection_state(instance_name)

        # Extract state from response: {"instance": {"state": "open"}}
        connection_state = state_response.get("instance", {}).get("state", "close")

        # Map Evolution API status to our status enum
        if connection_state == "open":
            real_time_status = IntegrationStatus.CONNECTED.value
        elif connection_state == "connecting":
            real_time_status = IntegrationStatus.CONNECTING.value
        else:
            real_time_status = IntegrationStatus.DISCONNECTED.value

        # Sync database if status differs (fix stale data)
        if integration.status != real_time_status:
            logger.info(
                f"Syncing WhatsApp status for bot {bot_id}: "
                f"DB={integration.status} -> Evolution={real_time_status}"
            )
            integration.status = real_time_status

            # Update connected_at timestamp
            if real_time_status == IntegrationStatus.CONNECTED.value and not integration.connected_at:
                integration.connected_at = datetime.now(timezone.utc)
            elif real_time_status != IntegrationStatus.CONNECTED.value:
                integration.connected_at = None

            await db.commit()

        return WhatsAppStatusResponse(
            status=real_time_status,
            instance_name=instance_name,
            phone_number=integration.config.get('phone_number'),
            connected_at=integration.connected_at
        )

    except EvolutionAPIError as e:
        # Evolution API unreachable or instance not found
        # Fall back to database status but log the issue
        logger.warning(
            f"Failed to query Evolution API for bot {bot_id}: {e}. "
            f"Returning database status: {integration.status}"
        )

        return WhatsAppStatusResponse(
            status=integration.status or IntegrationStatus.DISCONNECTED.value,
            instance_name=instance_name,
            phone_number=integration.config.get('phone_number'),
            connected_at=integration.connected_at
        )


@router.post("/{bot_id}/whatsapp/disconnect", response_model=WhatsAppStatusResponse)
async def disconnect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect WhatsApp. Updates database first, then cleans up Evolution API."""
    await verify_bot_ownership(db, bot_id, current_user.user_id)
    integration = await get_or_create_whatsapp_integration(db, bot_id)

    instance_name = integration.config.get('instance_name')
    if not instance_name:
        return WhatsAppStatusResponse(
            status=IntegrationStatus.DISCONNECTED.value,
            message="Not connected to WhatsApp"
        )

    # Update database first (ensures status is saved even if Evolution API fails)
    update_integration_config(integration, {}, ['instance_name', 'phone_number'])
    integration.status = IntegrationStatus.DISCONNECTED.value
    integration.connected_at = None
    await db.commit()
    logger.info(f"Bot {bot_id} marked as DISCONNECTED")

    # Clean up Evolution API (best effort)
    try:
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)
        await evolution_service.force_delete_instance(instance_name)
    except Exception as e:
        logger.warning(f"Error cleaning up Evolution instance {instance_name}: {e}")

    return WhatsAppStatusResponse(
        status=IntegrationStatus.DISCONNECTED.value,
        message="WhatsApp disconnected"
    )


@router.post("/{bot_id}/whatsapp/reconnect", response_model=WhatsAppStatusResponse)
async def reconnect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reconnect WhatsApp. Deletes existing instance and creates new one with fresh QR code."""
    if not settings.evolution_api.enabled:
        raise service_unavailable("WhatsApp integration is currently disabled")

    await verify_bot_ownership(db, bot_id, current_user.user_id)
    integration = await get_or_create_whatsapp_integration(db, bot_id)

    instance_name = f"bot_{str(bot_id).replace('-', '_')}"
    webhook_url = f"{settings.evolution_api.webhook_base_url}/evolution-webhooks"

    try:
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # Clean up existing instance
        await evolution_service.force_delete_instance(instance_name)

        # Create new instance
        instance_response = await create_evolution_instance(evolution_service, instance_name, webhook_url)

        # Extract QR code
        qr_data = instance_response.get("qrcode", {})
        qr_code = qr_data.get("base64") or qr_data.get("code")

        # Update integration
        update_integration_config(integration, {'instance_name': instance_name}, ['phone_number'])
        integration.status = IntegrationStatus.CONNECTING.value
        integration.connected_at = None
        await db.commit()

        return WhatsAppStatusResponse(
            status=IntegrationStatus.CONNECTING.value,
            instance_name=instance_name,
            qr_code=qr_code,
            message="Scan QR code with WhatsApp"
        )

    except EvolutionAPIError as e:
        logger.error(f"Evolution API error reconnecting bot {bot_id}: {e}")
        raise bad_gateway(f"Evolution API error: {e}")
    except Exception as e:
        logger.error(f"Error reconnecting WhatsApp for bot {bot_id}: {e}", exc_info=True)
        raise internal_server_error("Failed to reconnect")
