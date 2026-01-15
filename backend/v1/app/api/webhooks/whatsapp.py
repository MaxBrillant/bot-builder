"""
WhatsApp Webhooks

Handles Evolution API webhook events:
1. Message webhooks - incoming WhatsApp messages routed through bot engine
2. System webhooks - QR codes and connection status updates
"""

from fastapi import APIRouter, Depends, Request, Header
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.bot_service import BotService
from app.services.integrations.manager import IntegrationManager
from app.repositories.bot_integration_repository import BotIntegrationRepository
from app.core.engine import ConversationOrchestrator, get_http_client
from app.core.redis_manager import redis_manager, get_redis_manager
from app.config import settings
from app.utils.constants import IntegrationPlatform, IntegrationStatus
from app.utils.logger import logger
from app.utils.exceptions import NotFoundError
from app.schemas.evolution_webhook_schema import WebhookResponse
from app.utils.security import sanitize_input, check_suspicious_patterns

router = APIRouter(tags=["webhooks-whatsapp"])


def extract_bot_id_from_instance_name(instance_name: str) -> UUID:
    """Extract bot_id from instance_name format: bot_550e8400_e29b_41d4_a716_446655440000"""
    if not instance_name or not instance_name.startswith("bot_"):
        raise ValueError(f"Invalid instance name format: {instance_name}")
    bot_id_str = instance_name.replace("bot_", "").replace("_", "-")
    return UUID(bot_id_str)


@router.post("/webhooks/whatsapp/{bot_id}")
async def receive_whatsapp_message(
    bot_id: UUID,
    webhook_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive WhatsApp messages from Evolution API.

    Normalizes the message, processes through the bot engine,
    and sends the response back via WhatsApp.
    """
    bot_service = BotService(db)

    try:
        bot = await bot_service.get_bot(bot_id, check_ownership=False)
    except NotFoundError:
        logger.error(f"WhatsApp webhook - bot not found: {bot_id}")
        return {"status": "error", "message": "Bot not found"}

    if not bot.is_active():
        logger.info(f"WhatsApp webhook call to inactive bot: {bot_id}")
        return {"status": "error", "message": "Bot is currently inactive"}

    http_client = await get_http_client()
    integration_manager = IntegrationManager(db, http_client)

    # Normalize Evolution API webhook to platform-agnostic format
    normalized_message = integration_manager.normalize_webhook(
        IntegrationPlatform.WHATSAPP,
        webhook_data
    )

    if not normalized_message:
        logger.debug(f"WhatsApp message filtered out for bot {bot_id}")
        return {"status": "ignored", "message": "Message filtered"}

    # Rate limiting
    if settings.redis.enabled and redis_manager.is_connected():
        allowed = await redis_manager.check_rate_limit_channel_user(
            normalized_message["channel"],
            normalized_message["channel_user_id"],
            settings.rate_limit.webhook_max,
            settings.rate_limit.webhook_window
        )
        if not allowed:
            logger.warning(f"Rate limit exceeded for WhatsApp user", bot_id=str(bot_id))
            return {"status": "error", "message": "Rate limit exceeded"}

    # Input Sanitization (Layer 1 + Layer 3) - Per spec Section 10.1
    original_message = normalized_message["message_text"]

    # Layer 1: Baseline sanitization
    sanitized_message, sanitization_metadata = sanitize_input(original_message)

    # Log if significant sanitization occurred
    if (sanitization_metadata['null_bytes_removed'] > 0 or
        sanitization_metadata['control_chars_removed'] > 0 or
        sanitization_metadata['was_truncated']):
        logger.info(
            "Input sanitized (Layer 1) - WhatsApp",
            bot_id=str(bot_id),
            user=logger.mask_pii(normalized_message["channel_user_id"], "user_id"),
            null_bytes_removed=sanitization_metadata['null_bytes_removed'],
            control_chars_removed=sanitization_metadata['control_chars_removed'],
            was_truncated=sanitization_metadata['was_truncated']
        )

    # Layer 3: Pattern rejection
    is_safe, pattern_type = check_suspicious_patterns(sanitized_message)
    if not is_safe:
        logger.warning(
            "Suspicious pattern detected (Layer 3) - WhatsApp",
            bot_id=str(bot_id),
            user=logger.mask_pii(normalized_message["channel_user_id"], "user_id"),
            pattern_type=pattern_type
        )
        # Send error response via WhatsApp
        await integration_manager.send_message(
            platform=IntegrationPlatform.WHATSAPP,
            bot_id=bot_id,
            channel_user_id=normalized_message["channel_user_id"],
            message_text="Invalid characters detected. Please try again."
        )
        return {"status": "error", "message": "Suspicious pattern detected"}

    # Update message with sanitized version
    normalized_message["message_text"] = sanitized_message

    # Process through conversation engine
    try:
        orchestrator = ConversationOrchestrator(db)
        result = await orchestrator.process_message(
            channel=normalized_message["channel"],
            channel_user_id=normalized_message["channel_user_id"],
            bot_id=bot_id,
            message=normalized_message["message_text"]
        )

        # Send response
        messages = result.get("messages", [])
        response_text = "\n\n".join(messages) if messages else ""

        if response_text:
            await integration_manager.send_message(
                platform=IntegrationPlatform.WHATSAPP,
                bot_id=bot_id,
                channel_user_id=normalized_message["channel_user_id"],
                message_text=response_text
            )

        return {
            "status": "success",
            "message": "Message processed",
            "session_id": result.get("session_id")
        }

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", bot_id=str(bot_id), exc_info=True)
        return {"status": "error", "message": "An error occurred processing your message"}


@router.post("/evolution-webhooks", response_model=WebhookResponse)
async def receive_evolution_system_event(
    request: Request,
    x_instance_token: Optional[str] = Header(None, alias="X-Instance-Token")
):
    """
    Receive Evolution API system events (QR codes, connection updates).

    Events:
    - QRCODE_UPDATED: Stores QR code in Redis
    - CONNECTION_UPDATE: Updates connection status in database
    """
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Evolution webhook JSON: {e}")
        return WebhookResponse(
            status="error",
            message="Invalid JSON payload",
            timestamp=datetime.now(timezone.utc)
        )

    raw_event_type = event_data.get("event", "")
    event_type = raw_event_type.upper().replace(".", "_")
    instance_name = event_data.get("instance")

    logger.info(f"Evolution webhook: {event_type} for {instance_name}")

    # Validate token if instance exists
    if instance_name:
        async for db in get_db():
            try:
                bot_id = extract_bot_id_from_instance_name(instance_name)
                repo = BotIntegrationRepository(db)
                integration = await repo.get_by_bot_and_platform(bot_id, IntegrationPlatform.WHATSAPP)

                if integration:
                    expected_token = integration.config.get('instance_token')
                    if expected_token and x_instance_token != expected_token:
                        logger.warning(f"Invalid webhook token for {instance_name}")
                        return WebhookResponse(
                            status="error",
                            message="Invalid token",
                            timestamp=datetime.now(timezone.utc)
                        )
            except Exception as e:
                logger.warning(f"Could not validate token: {e}")
            break

    # Route to handler
    try:
        if event_type == "QRCODE_UPDATED":
            await handle_qrcode_updated(event_data)
        elif event_type == "CONNECTION_UPDATE":
            await handle_connection_update(event_data)
        elif event_type == "MESSAGES_UPSERT":
            logger.warning("MESSAGES_UPSERT at system webhook - should use /webhooks/whatsapp/{bot_id}")
        else:
            logger.debug(f"Unhandled event type: {event_type}")
    except Exception as e:
        logger.error(f"Error handling {event_type}: {e}", exc_info=True)

    return WebhookResponse(
        status="received",
        message=f"Processed {event_type}",
        timestamp=datetime.now(timezone.utc)
    )


async def handle_qrcode_updated(event_data: Dict[str, Any]):
    """Store QR code in Redis for frontend retrieval."""
    instance_name = event_data.get("instance")
    qr_data = event_data.get("data", {})

    qr_code = (
        qr_data.get("qrcode") or
        qr_data.get("code") or
        qr_data.get("base64") or
        qr_data.get("qr") or
        qr_data.get("pairingCode")
    )

    if not qr_code:
        logger.error(f"No QR code in event data")
        return

    try:
        bot_id = extract_bot_id_from_instance_name(instance_name)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to extract bot_id: {e}")
        return

    try:
        redis = get_redis_manager()
        await redis.store_qr_code(
            bot_id=str(bot_id),
            qr_code=qr_code,
            instance_name=instance_name,
            ttl=120
        )
        logger.info(f"QR code stored for bot {bot_id}")
    except Exception as e:
        logger.error(f"Failed to store QR code: {e}", exc_info=True)


async def handle_connection_update(event_data: Dict[str, Any]):
    """Update bot_integrations table with connection status."""
    instance_name = event_data.get("instance")
    connection_data = event_data.get("data", {})
    state = connection_data.get("state", "").lower()

    logger.info(f"Connection update for {instance_name}: {state}")

    try:
        bot_id = extract_bot_id_from_instance_name(instance_name)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to extract bot_id: {e}")
        return

    try:
        async for db in get_db():
            repo = BotIntegrationRepository(db)
            integration = await repo.get_by_bot_and_platform(bot_id, IntegrationPlatform.WHATSAPP)

            if not integration:
                logger.warning(f"No WhatsApp integration for bot {bot_id}")
                return

            if state == "open":
                integration.status = IntegrationStatus.CONNECTED.value
                integration.connected_at = datetime.now(timezone.utc)

                # Extract phone number
                instance_info = connection_data.get("instance", {})
                if isinstance(instance_info, dict):
                    phone = instance_info.get("owner") or instance_info.get("phoneNumber")
                    if phone:
                        config = integration.config.copy()
                        config["phone_number"] = phone
                        integration.config = config

                logger.info(f"Bot {bot_id} connected")

            elif state == "close":
                # Only disconnect if was connected (not during QR flow)
                if integration.status == IntegrationStatus.CONNECTED.value:
                    integration.status = IntegrationStatus.DISCONNECTED.value
                    integration.connected_at = None
                    config = integration.config.copy()
                    config.pop("phone_number", None)
                    integration.config = config
                    logger.info(f"Bot {bot_id} disconnected")

            elif state == "connecting":
                # Don't override DISCONNECTED (user initiated disconnect)
                if integration.status != IntegrationStatus.DISCONNECTED.value:
                    integration.status = IntegrationStatus.CONNECTING.value
                    logger.info(f"Bot {bot_id} connecting")

            else:
                logger.warning(f"Unknown connection state: {state}")
                return

            integration.last_sync_at = datetime.now(timezone.utc)
            await db.commit()
            break

    except Exception as e:
        logger.error(f"Failed to update connection status: {e}", exc_info=True)
