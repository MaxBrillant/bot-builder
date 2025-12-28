"""
Evolution API Webhook Receiver
Handles webhook events from Evolution API v2.2.3
"""

from fastapi import APIRouter, Header, HTTPException, status, Request
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.logger import get_logger
from app.core.redis_manager import get_redis_manager
from app.database import get_db
from app.models.bot import Bot
from app.schemas.evolution_webhook_schema import WebhookResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/evolution-webhooks", tags=["evolution-webhooks"])


@router.post("/", response_model=WebhookResponse)
async def receive_evolution_webhook(
    request: Request,
    apikey: Optional[str] = Header(None)
):
    """
    Receive webhook events from Evolution API v2.2.3

    This endpoint receives asynchronous events from Evolution API including:
    - QRCODE_UPDATED: QR code for WhatsApp connection (stored in Redis)
    - CONNECTION_UPDATE: Connection state changes (updates bot status in DB)
    - MESSAGES_UPSERT: Incoming messages (forwarded to bot's conversation engine)

    Authentication: DISABLED - Evolution API v2.2.3 does not support custom headers
    Security: Relies on Docker network isolation (only Evolution API container can reach this endpoint)

    Returns:
        WebhookResponse with status "received"
    """
    # NOTE: Authentication disabled because Evolution API v2.2.3 cannot send custom headers
    # Security relies on Docker network isolation - only Evolution API container can reach this endpoint
    logger.info(f"Webhook received from Evolution API (apikey header present: {apikey is not None})")

    # Parse event data
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Normalize event name: handle both formats (qrcode.updated, QRCODE_UPDATED)
    raw_event_type = event_data.get("event", "")
    event_type = raw_event_type.upper().replace(".", "_")
    instance_name = event_data.get("instance")

    logger.info(f"Received Evolution webhook: {event_type} for {instance_name}")
    logger.debug(f"Event data: {event_data}")

    # Route to appropriate handler
    try:
        if event_type == "QRCODE_UPDATED":
            await handle_qrcode_updated(event_data)
        elif event_type == "CONNECTION_UPDATE":
            await handle_connection_update(event_data)
        elif event_type == "MESSAGES_UPSERT":
            await handle_message_upsert(event_data)
        else:
            logger.info(f"Unhandled event type: {event_type} (raw: {raw_event_type})")
    except Exception as e:
        logger.error(f"Error handling webhook event {event_type}: {str(e)}", exc_info=True)
        # Don't raise exception - return 200 to Evolution API to prevent retries
        # Log the error for debugging but acknowledge receipt

    return WebhookResponse(
        status="received",
        message=f"Processed {event_type} event",
        timestamp=datetime.now(timezone.utc)
    )


async def handle_qrcode_updated(event_data: Dict[str, Any]):
    """
    Handle QRCODE_UPDATED event

    Stores QR code in Redis for frontend retrieval.
    QR codes have a 60-second TTL since they expire quickly.
    """
    instance_name = event_data.get("instance")
    qr_data = event_data.get("data", {})

    # Try multiple field names for QR code
    qr_code = (
        qr_data.get("qrcode") or
        qr_data.get("code") or
        qr_data.get("base64") or
        qr_data.get("qr") or
        qr_data.get("pairingCode")  # Some versions use pairing codes
    )

    if not qr_code:
        logger.error(f"No QR code found in event data: {event_data}")
        return

    # Extract bot_id from instance_name (format: bot_uuid_with_underscores)
    # Example: bot_550e8400_e29b_41d4_a716_446655440000 -> 550e8400-e29b-41d4-a716-446655440000
    if not instance_name or not instance_name.startswith("bot_"):
        logger.error(f"Invalid instance name format: {instance_name}")
        return

    bot_id_str = instance_name.replace("bot_", "").replace("_", "-")

    try:
        # Validate bot_id is a valid UUID
        bot_id = UUID(bot_id_str)
    except ValueError:
        logger.error(f"Invalid bot_id derived from instance name: {bot_id_str}")
        return

    # Store QR code in Redis with 60 second TTL
    try:
        redis_manager = get_redis_manager()
        await redis_manager.store_qr_code(
            bot_id=str(bot_id),
            qr_code=qr_code,
            instance_name=instance_name,
            ttl=60
        )
        logger.info(f"Stored QR code for bot {bot_id} in Redis (TTL: 60s)")
    except Exception as e:
        logger.error(f"Failed to store QR code in Redis: {str(e)}", exc_info=True)


async def handle_connection_update(event_data: Dict[str, Any]):
    """
    Handle CONNECTION_UPDATE event

    Updates bot connection status in database when WhatsApp connection state changes.

    States:
    - "open" -> connected (phone scanned QR code successfully)
    - "close" -> disconnected (phone disconnected or logged out)
    - "connecting" -> pending (waiting for QR code scan)
    """
    instance_name = event_data.get("instance")
    connection_data = event_data.get("data", {})
    state = connection_data.get("state", "").lower()

    logger.info(f"Connection update for {instance_name}: {state}")

    # Extract bot_id from instance_name
    if not instance_name or not instance_name.startswith("bot_"):
        logger.error(f"Invalid instance name format: {instance_name}")
        return

    bot_id_str = instance_name.replace("bot_", "").replace("_", "-")

    try:
        bot_id = UUID(bot_id_str)
    except ValueError:
        logger.error(f"Invalid bot_id derived from instance name: {bot_id_str}")
        return

    # Update bot status in database
    try:
        async for db in get_db():
            result = await db.execute(
                select(Bot).where(Bot.bot_id == bot_id)
            )
            bot = result.scalar_one_or_none()

            if not bot:
                logger.warning(f"Bot not found for instance {instance_name}: {bot_id}")
                return

            # Map Evolution API state to bot status
            if state == "open":
                bot.evolution_instance_status = "connected"
                bot.whatsapp_connected_at = datetime.now(timezone.utc)

                # Extract phone number if available
                # In Evolution API v2.2.3, connection_data.instance can be a string (instance name) or dict
                instance_info = connection_data.get("instance", {})
                if isinstance(instance_info, dict):
                    phone = instance_info.get("owner") or instance_info.get("profilePictureUrl")
                    if phone and not bot.whatsapp_phone_number:
                        bot.whatsapp_phone_number = phone
                else:
                    logger.debug(f"Instance info is not a dict: {type(instance_info)}")

                logger.info(f"Bot {bot_id} connected to WhatsApp")

            elif state == "close":
                bot.evolution_instance_status = "disconnected"
                bot.whatsapp_phone_number = None
                bot.whatsapp_connected_at = None
                logger.info(f"Bot {bot_id} disconnected from WhatsApp")

            elif state == "connecting":
                bot.evolution_instance_status = "connecting"
                logger.info(f"Bot {bot_id} is connecting (waiting for QR scan)")

            else:
                logger.warning(f"Unknown connection state: {state}")

            await db.commit()
            logger.info(f"Updated bot {bot_id} status to {bot.evolution_instance_status}")
            break  # Exit after first (and only) iteration

    except Exception as e:
        logger.error(f"Failed to update bot status for {instance_name}: {str(e)}", exc_info=True)


async def handle_message_upsert(event_data: Dict[str, Any]):
    """
    Handle MESSAGES_UPSERT event

    Receives incoming WhatsApp messages and forwards them to the bot's
    conversation engine via the existing webhook system.

    This will be fully implemented in a later phase when message routing is set up.
    For now, we just log the event.
    """
    instance_name = event_data.get("instance")
    message_data = event_data.get("data", {})

    logger.info(f"Message upsert event for {instance_name}")
    logger.debug(f"Message data: {message_data}")

    # TODO: Future implementation
    # 1. Extract bot_id from instance_name
    # 2. Parse message content (text, media, etc.)
    # 3. Extract sender phone number
    # 4. Call conversation engine with normalized message
    # 5. Return bot response via Evolution API send_message

    # For now, just acknowledge receipt
    logger.info(f"Message received for {instance_name} (handler not yet implemented)")
