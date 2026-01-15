"""
Core Platform-Agnostic Webhook API
ONLY receives normalized messages from integration layers
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.bot_service import BotService
from app.core.engine import ConversationOrchestrator
from app.core.redis_manager import redis_manager
from app.config import settings
from app.schemas.webhook_schema import WebhookMessageRequest, WebhookMessageResponse
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.audit_log import AuditResult
from app.utils.exceptions import NotFoundError
from app.utils.logger import logger
from app.utils.security import sanitize_input, check_suspicious_patterns, SanitizationError

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/{bot_id}", response_model=WebhookMessageResponse)
async def process_bot_message(
    bot_id: UUID,
    message_data: WebhookMessageRequest,
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db)
):
    """
    CORE PLATFORM-AGNOSTIC WEBHOOK ENDPOINT

    This is the ONLY core webhook endpoint. It processes messages in a
    completely platform-agnostic manner.

    **Who calls this endpoint:**
    - Integration layer webhooks (after normalizing platform-specific data)
    - External services that already provide normalized format
    - Testing tools

    **Architecture:**
    ```
    Platform Webhook → Integration Layer → Normalize → /webhook/{bot_id}
                                                            ↓
                                                      Core Engine
                                                            ↓
                                                      Return Response
                                                            ↓
                                           Integration Layer → Platform API
    ```

    **Authentication:**
    Requires X-Webhook-Secret header matching bot's webhook_secret

    **Request Body (Normalized Format):**
    ```json
    {
        "channel": "whatsapp",          // Platform identifier
        "channel_user_id": "+254...",   // Platform-specific user ID
        "message_text": "Hello bot"     // Message content
    }
    ```

    **Response:**
    ```json
    {
        "status": "success",
        "response_text": "Bot's response",
        "session_id": "uuid"
    }
    ```

    **Design Note:**
    This endpoint has ZERO knowledge of:
    - WhatsApp, Telegram, Slack, or any specific platform
    - Phone numbers, user handles, or platform-specific identifiers
    - Platform APIs or SDKs

    All platform-specific logic is isolated in the integration layer.
    """

    # 1. Validate webhook secret
    if not x_webhook_secret:
        logger.warning(f"Webhook request without secret header: bot={bot_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Webhook-Secret header is required"
        )

    bot_service = BotService(db)
    audit_log = AuditLogRepository(db)

    # 2. Verify webhook authentication
    is_valid = await bot_service.verify_webhook_secret(bot_id, x_webhook_secret)
    if not is_valid:
        logger.warning(f"Invalid webhook secret: bot={bot_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret"
        )

    # 3. Get bot and verify existence
    try:
        bot = await bot_service.get_bot(bot_id, check_ownership=False)
    except NotFoundError:
        logger.error(f"Bot not found: {bot_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot {bot_id} not found"
        )

    # 4. Check bot status
    if not bot.is_active():
        logger.info(f"Webhook call to inactive bot: {bot_id}")
        return WebhookMessageResponse(
            status="error",
            error="Bot is currently inactive"
        )

    # 5. Rate limiting (channel-agnostic)
    if settings.redis.enabled and redis_manager.is_connected():
        allowed = await redis_manager.check_rate_limit_channel_user(
            message_data.channel,
            message_data.channel_user_id,
            settings.rate_limit.webhook_max,
            settings.rate_limit.webhook_window
        )
        if not allowed:
            masked_user = logger.mask_pii(message_data.channel_user_id, "user_id")
            logger.warning(
                f"Rate limit exceeded",
                channel=message_data.channel,
                user=masked_user
            )
            # Audit log: rate limiting security event
            await audit_log.log_security_event(
                action="rate_limit_exceeded",
                user_id=masked_user,
                result=AuditResult.BLOCKED,
                metadata={
                    "bot_id": str(bot_id),
                    "channel": message_data.channel
                }
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )

    # 6. Input Sanitization (Layer 1 + Layer 3)
    # Apply universal sanitization rules per spec Section 10.1
    original_message = message_data.message_text

    # Layer 1: Baseline sanitization (null bytes, control chars, trim, length limit)
    sanitized_message, sanitization_metadata = sanitize_input(original_message)

    # Masked user ID for logging (reused below)
    masked_user_id = logger.mask_pii(message_data.channel_user_id, "user_id")

    # Log if significant sanitization occurred
    if (sanitization_metadata['null_bytes_removed'] > 0 or
        sanitization_metadata['control_chars_removed'] > 0 or
        sanitization_metadata['was_truncated']):
        logger.info(
            "Input sanitized (Layer 1)",
            bot_id=str(bot_id),
            channel=message_data.channel,
            user=masked_user_id,
            null_bytes_removed=sanitization_metadata['null_bytes_removed'],
            control_chars_removed=sanitization_metadata['control_chars_removed'],
            was_truncated=sanitization_metadata['was_truncated'],
            original_length=sanitization_metadata['original_length'],
            sanitized_length=sanitization_metadata['sanitized_length']
        )
        # Audit log: input sanitization security event
        await audit_log.log_security_event(
            action="input_sanitized",
            user_id=masked_user_id,
            result=AuditResult.SUCCESS,
            metadata={
                "bot_id": str(bot_id),
                "channel": message_data.channel,
                "null_bytes_removed": sanitization_metadata['null_bytes_removed'],
                "control_chars_removed": sanitization_metadata['control_chars_removed'],
                "was_truncated": sanitization_metadata['was_truncated']
            }
        )

    # Layer 3: Pattern rejection (check for attack patterns)
    is_safe, pattern_type = check_suspicious_patterns(sanitized_message)
    if not is_safe:
        logger.warning(
            "Suspicious pattern detected (Layer 3)",
            bot_id=str(bot_id),
            channel=message_data.channel,
            user=masked_user_id,
            pattern_type=pattern_type,
            input_length=len(sanitized_message)
        )
        # Audit log: suspicious pattern security event
        await audit_log.log_security_event(
            action="pattern_rejected",
            user_id=masked_user_id,
            result=AuditResult.BLOCKED,
            metadata={
                "bot_id": str(bot_id),
                "channel": message_data.channel,
                "pattern_type": pattern_type,
                "input_length": len(sanitized_message)
            }
        )
        # Return error response (does not count toward validation retries - handled at engine level)
        return WebhookMessageResponse(
            status="error",
            error="Invalid characters detected. Please try again."
        )

    # Update message with sanitized version for processing
    message_data.message_text = sanitized_message

    # 7. Process through conversation engine (platform-agnostic)
    try:
        orchestrator = ConversationOrchestrator(db)

        result = await orchestrator.process_message(
            channel=message_data.channel,
            channel_user_id=message_data.channel_user_id,
            bot_id=bot_id,
            message=message_data.message_text
        )

        logger.info(
            f"Message processed successfully",
            bot_id=str(bot_id),
            channel=message_data.channel,
            session_id=result.get("session_id")
        )

        # 8. Join multiple messages into single response
        messages = result.get("messages", [])
        response_text = "\n\n".join(messages) if messages else ""

        return WebhookMessageResponse(
            status="success",
            response_text=response_text,
            session_id=result.get("session_id")
        )

    except Exception as e:
        logger.error(
            f"Error processing message: {str(e)}",
            bot_id=str(bot_id),
            exc_info=True
        )
        return WebhookMessageResponse(
            status="error",
            error="An error occurred processing your message. Please try again."
        )
