"""
WhatsApp Management API
Endpoints for connecting and managing WhatsApp integrations via Evolution API
"""

from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.bot_service import BotService
from app.services.evolution_service import EvolutionAPIService, EvolutionAPIError
from app.schemas.whatsapp_schema import WhatsAppStatusResponse
from app.core.engine import get_http_client
from app.config import settings
from app.utils.exceptions import NotFoundError, UnauthorizedError
from app.utils.logger import get_logger
from app.core.redis_manager import get_redis_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/bots", tags=["whatsapp"])


@router.post("/{bot_id}/whatsapp/connect", response_model=WhatsAppStatusResponse)
async def connect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize WhatsApp connection using Evolution API v2.2.3

    **Evolution API v2.2.3 returns QR code immediately in create response.**

    Steps:
    1. Create Evolution API instance with webhook configuration
    2. Receive QR code immediately in response
    3. Return status "connecting" with QR code
    4. Evolution API sends updates via webhook (CONNECTION_UPDATE, MESSAGES_UPSERT)

    Returns:
        status: "connecting"
        instance_name: Evolution API instance identifier
        qr_code: QR code base64 image (ready to display immediately)
        message: Instructions for user

    Frontend Implementation:
        1. Call this endpoint to initiate connection
        2. Display QR code immediately (no polling needed!)
        3. Poll /bots/{bot_id}/whatsapp/status to detect when user scans QR
    """
    # Check if Evolution API is enabled
    if not settings.evolution_api.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp integration is currently disabled"
        )

    # Get bot and verify ownership
    bot_service = BotService(db)
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
    except (NotFoundError, UnauthorizedError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # Check if already connected
    if bot.evolution_instance_status == 'connected':
        return WhatsAppStatusResponse(
            status="connected",
            instance_name=bot.evolution_instance_name,
            phone_number=bot.whatsapp_phone_number,
            connected_at=bot.whatsapp_connected_at,
            message="Bot is already connected to WhatsApp. Disconnect first to reconnect."
        )

    # Check if already in connecting state - return current status
    if bot.evolution_instance_status == 'connecting' and bot.evolution_instance_name:
        logger.info(f"Bot {bot_id} is already in connecting state. Returning current status.")
        return WhatsAppStatusResponse(
            status="connecting",
            instance_name=bot.evolution_instance_name,
            message="Connection already in progress. Poll GET /bots/{bot_id}/whatsapp/qr-code to retrieve QR code."
        )

    # Generate unique instance name from bot_id
    instance_name = f"bot_{str(bot_id).replace('-', '_')}"

    # Configure webhook URL - points to our webhook receiver (with trailing slash to avoid 307 redirect)
    webhook_url = f"{settings.evolution_api.webhook_base_url}/evolution-webhooks/"

    try:
        # Initialize Evolution API service
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # If there's an old instance hanging around, try to delete it first
        if bot.evolution_instance_name:
            try:
                logger.info(f"Cleaning up old instance: {bot.evolution_instance_name}")
                await evolution_service.delete_instance(bot.evolution_instance_name)
            except EvolutionAPIError as e:
                logger.warning(f"Could not delete old instance: {str(e)}")

        # Define webhook events
        webhook_events = [
            "QRCODE_UPDATED",      # Receive QR codes (for regeneration)
            "CONNECTION_UPDATE",    # Receive connection status changes
            "MESSAGES_UPSERT"      # Receive incoming messages
        ]

        # Step 1: Create Evolution API instance WITH webhook configuration
        # v2.2.3: QR code returned immediately + webhooks for automatic updates
        logger.info(f"Creating Evolution API instance for bot {bot_id}: {instance_name}")
        logger.info(f"Webhook URL: {webhook_url}")
        logger.info(f"Webhook events: {webhook_events}")

        instance_response = await evolution_service.create_instance(
            instance_name=instance_name,
            integration="WHATSAPP-BAILEYS",
            qrcode=True,
            webhook_url=webhook_url,  # Updated parameter name for v2
            webhook_by_events=False,
            webhook_base64=False,  # We don't need base64 in webhook payloads
            events=webhook_events
        )
        logger.info(f"Instance created successfully: {instance_name}")

        # Step 2: Extract QR code from IMMEDIATE response
        # Evolution API v2.2.3 returns QR code in the create response
        qr_data = instance_response.get("qrcode", {})
        qr_code = qr_data.get("base64") or qr_data.get("code")

        if qr_code:
            logger.info(f"QR code received in create instance response for bot {bot_id} (length: {len(qr_code)} chars)")
        else:
            logger.warning(f"No QR code in create response for bot {bot_id}. Response: {instance_response}")

        # Step 3: Update bot status
        bot.evolution_instance_name = instance_name
        bot.evolution_instance_status = 'connecting'
        bot.whatsapp_phone_number = None
        bot.whatsapp_connected_at = None

        await db.commit()
        await db.refresh(bot)

        logger.info(f"WhatsApp connection initiated for bot {bot_id}. QR code available immediately.")
        return WhatsAppStatusResponse(
            status="connecting",
            instance_name=instance_name,
            qr_code=qr_code,  # QR code returned IMMEDIATELY
            message="Scan QR code with WhatsApp"
        )

    except EvolutionAPIError as e:
        logger.error(f"Evolution API error for bot {bot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting WhatsApp for bot {bot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate WhatsApp connection"
        )


@router.get("/{bot_id}/whatsapp/qr-code")
async def get_qr_code(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve QR code for WhatsApp connection

    This endpoint is polled by the frontend after calling POST /whatsapp/connect.
    Returns the QR code when Evolution API sends it via webhook (stored in Redis).

    Flow:
    1. Frontend calls POST /whatsapp/connect
    2. Frontend polls this endpoint every 2 seconds
    3. Evolution API sends QRCODE_UPDATED webhook
    4. Webhook handler stores QR code in Redis
    5. This endpoint returns stored QR code
    6. Frontend displays QR code for user to scan

    Returns:
        - 200: QR code found (includes qr_code, instance_name, timestamp)
        - 404: QR code not yet available (frontend should retry)
        - 400: Bot not in connecting state
    """
    # Get bot and verify ownership
    bot_service = BotService(db)
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
    except (NotFoundError, UnauthorizedError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # Check if instance is in connecting state
    if bot.evolution_instance_status != 'connecting':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot is not in connecting state. Current status: {bot.evolution_instance_status or 'disconnected'}"
        )

    # Check Redis for QR code
    redis_manager = get_redis_manager()
    qr_data = await redis_manager.get_qr_code(str(bot_id))

    if not qr_data:
        # QR code not yet available - frontend should retry
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not yet available. Please try again in a moment."
        )

    logger.info(f"Returning QR code for bot {bot_id}")

    return {
        "qr_code": qr_data["qr_code"],
        "instance_name": qr_data.get("instance_name", bot.evolution_instance_name),
        "timestamp": qr_data["timestamp"],
        "message": "Scan this QR code with WhatsApp to connect"
    }


@router.get("/{bot_id}/whatsapp/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check WhatsApp connection status for a bot

    Queries Evolution API for current connection state and updates bot record.

    State mapping:
    - Evolution API "open" → "connected"
    - Evolution API "close" → "disconnected"
    - Evolution API "connecting" → "connecting"

    Returns current status with phone number if connected.
    """
    # Get bot and verify ownership
    bot_service = BotService(db)
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
    except (NotFoundError, UnauthorizedError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # If no instance name, return disconnected
    if not bot.evolution_instance_name:
        return WhatsAppStatusResponse(
            status="disconnected",
            message="Bot is not connected to WhatsApp"
        )

    try:
        # Check connection state with Evolution API
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        state_response = await evolution_service.get_connection_state(bot.evolution_instance_name)
        api_state = state_response.get('state', '').lower()

        # Map Evolution API state to our status
        if api_state == 'open':
            new_status = 'connected'
            # Extract phone number if available
            instance_data = state_response.get('instance', {})
            phone_number = instance_data.get('owner') or bot.whatsapp_phone_number

            # Update bot if newly connected
            if bot.evolution_instance_status != 'connected':
                bot.evolution_instance_status = 'connected'
                bot.whatsapp_phone_number = phone_number
                bot.whatsapp_connected_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(bot)

        elif api_state == 'close':
            new_status = 'disconnected'
            # Update bot if status changed
            if bot.evolution_instance_status != 'disconnected':
                bot.evolution_instance_status = 'disconnected'
                bot.whatsapp_phone_number = None
                bot.whatsapp_connected_at = None
                await db.commit()
                await db.refresh(bot)

        elif api_state == 'connecting':
            new_status = 'connecting'
        else:
            new_status = bot.evolution_instance_status or 'disconnected'

        return WhatsAppStatusResponse(
            status=new_status,
            instance_name=bot.evolution_instance_name,
            phone_number=bot.whatsapp_phone_number,
            connected_at=bot.whatsapp_connected_at
        )

    except EvolutionAPIError as e:
        logger.error(f"Evolution API error checking status for bot {bot_id}: {str(e)}")
        # Return current bot status as fallback
        return WhatsAppStatusResponse(
            status=bot.evolution_instance_status or 'error',
            instance_name=bot.evolution_instance_name,
            phone_number=bot.whatsapp_phone_number,
            connected_at=bot.whatsapp_connected_at,
            message="Could not verify status with Evolution API"
        )
    except Exception as e:
        logger.error(f"Unexpected error checking WhatsApp status for bot {bot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check WhatsApp status"
        )


@router.post("/{bot_id}/whatsapp/disconnect", response_model=WhatsAppStatusResponse)
async def disconnect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect WhatsApp connection for a bot

    Steps:
    1. Logout from Evolution API (disconnects WhatsApp)
    2. Delete the Evolution API instance
    3. Clear bot's WhatsApp fields
    4. Return disconnected status

    This is a destructive operation - the bot will need to reconnect
    with a new QR code.
    """
    # Get bot and verify ownership
    bot_service = BotService(db)
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
    except (NotFoundError, UnauthorizedError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # Check if there's an instance to disconnect
    if not bot.evolution_instance_name:
        return WhatsAppStatusResponse(
            status="disconnected",
            message="Bot is not connected to WhatsApp"
        )

    try:
        # Initialize Evolution API service
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # Try to logout (disconnect WhatsApp)
        try:
            await evolution_service.logout_instance(bot.evolution_instance_name)
            logger.info(f"Logged out Evolution API instance: {bot.evolution_instance_name}")
        except EvolutionAPIError as e:
            logger.warning(f"Could not logout instance (may not exist): {str(e)}")

        # Try to delete instance
        try:
            await evolution_service.delete_instance(bot.evolution_instance_name)
            logger.info(f"Deleted Evolution API instance: {bot.evolution_instance_name}")
        except EvolutionAPIError as e:
            logger.warning(f"Could not delete instance (may not exist): {str(e)}")

        # Clear bot WhatsApp fields
        bot.evolution_instance_name = None
        bot.evolution_instance_status = 'disconnected'
        bot.whatsapp_phone_number = None
        bot.whatsapp_connected_at = None

        await db.commit()
        await db.refresh(bot)

        logger.info(f"Successfully disconnected WhatsApp for bot {bot_id}")

        return WhatsAppStatusResponse(
            status="disconnected",
            message="WhatsApp disconnected successfully"
        )

    except Exception as e:
        logger.error(f"Unexpected error disconnecting WhatsApp for bot {bot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect WhatsApp"
        )


@router.post("/{bot_id}/whatsapp/reconnect", response_model=WhatsAppStatusResponse)
async def reconnect_whatsapp(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reconnect WhatsApp for a bot using Evolution API v2.2.3

    Useful for troubleshooting or switching WhatsApp numbers.

    Steps:
    1. Disconnect current WhatsApp connection (logout + delete instance)
    2. Create new Evolution API instance with webhook configuration
    3. Return status "connecting" with QR code immediately
    4. Webhooks handle status updates automatically

    This is equivalent to disconnect + connect but in a single operation.
    """
    # Get bot and verify ownership
    bot_service = BotService(db)
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
    except (NotFoundError, UnauthorizedError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    # Check if Evolution API is enabled
    if not settings.evolution_api.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp integration is currently disabled"
        )

    try:
        # Initialize Evolution API service
        http_client = await get_http_client()
        evolution_service = EvolutionAPIService(http_client)

        # Disconnect if currently connected
        if bot.evolution_instance_name:
            try:
                await evolution_service.logout_instance(bot.evolution_instance_name)
                await evolution_service.delete_instance(bot.evolution_instance_name)
                logger.info(f"Disconnected old instance: {bot.evolution_instance_name}")
            except EvolutionAPIError as e:
                logger.warning(f"Could not disconnect old instance: {str(e)}")

        # Generate new instance name
        instance_name = f"bot_{str(bot_id).replace('-', '_')}"

        # Configure webhook URL (with trailing slash to avoid 307 redirect)
        webhook_url = f"{settings.evolution_api.webhook_base_url}/evolution-webhooks/"

        # Define webhook events
        webhook_events = [
            "QRCODE_UPDATED",      # Receive QR codes (for regeneration)
            "CONNECTION_UPDATE",    # Receive connection status changes
            "MESSAGES_UPSERT"      # Receive incoming messages
        ]

        # Step 1: Create new instance WITH webhook configuration
        # v2.2.3: QR code returned immediately + webhooks for automatic updates
        logger.info(f"Creating new Evolution API instance: {instance_name}")
        logger.info(f"Webhook URL: {webhook_url}")
        logger.info(f"Webhook events: {webhook_events}")

        instance_response = await evolution_service.create_instance(
            instance_name=instance_name,
            integration="WHATSAPP-BAILEYS",
            qrcode=True,
            webhook_url=webhook_url,  # Updated parameter name for v2
            webhook_by_events=False,
            webhook_base64=False,  # We don't need base64 in webhook payloads
            events=webhook_events
        )
        logger.info(f"Instance created successfully: {instance_name}")

        # Step 2: Extract QR code from IMMEDIATE response
        # Evolution API v2.2.3 returns QR code in the create response
        qr_data = instance_response.get("qrcode", {})
        qr_code = qr_data.get("base64") or qr_data.get("code")

        if qr_code:
            logger.info(f"QR code received in create instance response for bot {bot_id} (length: {len(qr_code)} chars)")
        else:
            logger.warning(f"No QR code in create response for bot {bot_id}. Response: {instance_response}")

        # Step 3: Update bot with new instance details
        bot.evolution_instance_name = instance_name
        bot.evolution_instance_status = 'connecting'
        bot.whatsapp_phone_number = None
        bot.whatsapp_connected_at = None

        await db.commit()
        await db.refresh(bot)

        logger.info(f"Successfully initiated WhatsApp reconnection for bot {bot_id}. QR code available immediately.")

        return WhatsAppStatusResponse(
            status="connecting",
            instance_name=instance_name,
            qr_code=qr_code,  # QR code returned IMMEDIATELY
            message="Scan QR code with WhatsApp"
        )

    except EvolutionAPIError as e:
        logger.error(f"Evolution API error reconnecting bot {bot_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error reconnecting WhatsApp for bot {bot_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reconnect WhatsApp"
        )
