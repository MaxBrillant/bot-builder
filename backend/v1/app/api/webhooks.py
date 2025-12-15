"""
Webhook API
Endpoint for processing bot messages via webhooks
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.bot_service import BotService
from app.core.conversation_engine import ConversationEngine
from app.core.redis_manager import redis_manager
from app.config import settings
from app.schemas.webhook_schema import WebhookMessageRequest, WebhookMessageResponse
from app.utils.exceptions import NotFoundError
from app.utils.logger import logger

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/{bot_id}", response_model=WebhookMessageResponse)
async def process_bot_message(
    bot_id: UUID,
    message_data: WebhookMessageRequest,
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db)
):
    """
    Process incoming message for a specific bot
    
    **Authentication**: Requires X-Webhook-Secret header matching bot's webhook_secret
    
    **Request Body**:
    - **channel**: Communication channel (e.g., 'whatsapp', 'telegram')
    - **channel_user_id**: Platform-specific user identifier
    - **message_text**: The message text from the user
    
    **Response**:
    - **status**: 'success' or 'error'
    - **response_text**: Text to send back to user
    - **session_id**: Session identifier
    - **error**: Error message (if status is 'error')
    
    **Example Request**:
    ```
    POST /webhook/550e8400-e29b-41d4-a716-446655440000
    Headers:
      X-Webhook-Secret: abc123...
      Content-Type: application/json
    
    Body:
    {
      "channel": "whatsapp",
      "channel_user_id": "+254712345678",
      "message_text": "START"
    }
    ```
    """
    
    # Validate webhook secret
    if not x_webhook_secret:
        logger.warning(f"Webhook call to bot {bot_id} without secret header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Webhook-Secret header is required"
        )
    
    bot_service = BotService(db)
    
    # Verify webhook authentication
    is_valid = await bot_service.verify_webhook_secret(bot_id, x_webhook_secret)
    if not is_valid:
        logger.warning(f"Invalid webhook secret for bot {bot_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret"
        )
    
    # Get bot and check status
    try:
        bot = await bot_service.get_bot(bot_id, check_ownership=False)
    except NotFoundError:
        logger.error(f"Bot {bot_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot {bot_id} not found"
        )
    
    # Check if bot is active
    if not bot.is_active():
        logger.info(f"Webhook call to inactive bot {bot_id}")
        return WebhookMessageResponse(
            status="error",
            error="Bot is currently inactive"
        )
    
    # Check rate limit for channel user
    if settings.REDIS_ENABLED and redis_manager.is_connected():
        allowed = await redis_manager.check_rate_limit_channel_user(
            message_data.channel,
            message_data.channel_user_id,
            settings.RATE_LIMIT_WEBHOOK_MAX,
            settings.RATE_LIMIT_WEBHOOK_WINDOW
        )
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {message_data.channel} user: {message_data.channel_user_id}",
                bot_id=str(bot_id)
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )
    
    # Process message through conversation engine
    try:
        conversation_engine = ConversationEngine(db)
        
        result = await conversation_engine.process_message(
            channel=message_data.channel,
            channel_user_id=message_data.channel_user_id,
            bot_id=bot_id,
            message=message_data.message_text
        )
        
        logger.info(
            f"Message processed for bot {bot_id}, "
            f"channel={message_data.channel}, "
            f"user={message_data.channel_user_id}"
        )
        
        # Join multiple messages into single response text
        # Conversation engine returns messages as array, join with newlines
        messages = result.get("messages", [])
        response_text = "\n\n".join(messages) if messages else ""
        
        return WebhookMessageResponse(
            status="success",
            response_text=response_text,
            session_id=result.get("session_id")
        )
        
    except Exception as e:
        logger.error(f"Error processing message for bot {bot_id}: {str(e)}", exc_info=True)
        return WebhookMessageResponse(
            status="error",
            error="An error occurred processing your message. Please try again."
        )