"""
Shared webhook input sanitization and security validation.

Provides Layer 1 (baseline sanitization) and Layer 3 (pattern rejection)
security controls for all webhook endpoints.
"""

from typing import Tuple, Optional
from uuid import UUID

from app.utils.security import sanitize_input, check_suspicious_patterns
from app.utils.logger import logger
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.audit_log import AuditResult


async def sanitize_and_audit_webhook_input(
    message: str,
    bot_id: UUID,
    channel: str,
    channel_user_id: str,
    audit_log: Optional[AuditLogRepository] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Sanitize webhook input and check for suspicious patterns.

    Applies security layers:
    - Layer 1: Baseline sanitization (null bytes, control chars, truncation)
    - Layer 3: Pattern rejection (SQL injection, XSS, path traversal, etc.)

    Args:
        message: Raw input message to sanitize
        bot_id: Bot ID for logging context
        channel: Channel identifier for logging
        channel_user_id: User identifier (will be masked in logs)
        audit_log: Optional audit log repository for security event logging

    Returns:
        Tuple of (is_safe, sanitized_message, error_message)
        - is_safe: False if suspicious patterns detected, True otherwise
        - sanitized_message: Cleaned message text
        - error_message: User-facing error message if not safe, None otherwise
    """
    # Layer 1: Baseline sanitization
    sanitized_message, sanitization_metadata = sanitize_input(message)
    masked_user_id = logger.mask_pii(channel_user_id, "user_id")

    # Log and audit significant sanitization
    if (sanitization_metadata['null_bytes_removed'] > 0 or
        sanitization_metadata['control_chars_removed'] > 0 or
        sanitization_metadata['was_truncated']):

        logger.info(
            "Input sanitized (Layer 1)",
            bot_id=str(bot_id),
            channel=channel,
            user=masked_user_id,
            null_bytes_removed=sanitization_metadata['null_bytes_removed'],
            control_chars_removed=sanitization_metadata['control_chars_removed'],
            was_truncated=sanitization_metadata['was_truncated'],
            original_length=sanitization_metadata['original_length'],
            sanitized_length=sanitization_metadata['sanitized_length']
        )

        # Audit if repository provided
        if audit_log:
            await audit_log.log_security_event(
                action="input_sanitized",
                user_id=masked_user_id,
                result=AuditResult.SUCCESS,
                event_metadata={
                    "bot_id": str(bot_id),
                    "channel": channel,
                    "null_bytes_removed": sanitization_metadata['null_bytes_removed'],
                    "control_chars_removed": sanitization_metadata['control_chars_removed'],
                    "was_truncated": sanitization_metadata['was_truncated']
                }
            )

    # Layer 3: Pattern rejection
    is_safe, pattern_type = check_suspicious_patterns(sanitized_message)
    if not is_safe:
        logger.warning(
            "Suspicious pattern detected (Layer 3)",
            bot_id=str(bot_id),
            channel=channel,
            user=masked_user_id,
            pattern_type=pattern_type,
            input_length=len(sanitized_message)
        )

        # Audit if repository provided
        if audit_log:
            await audit_log.log_security_event(
                action="pattern_rejected",
                user_id=masked_user_id,
                result=AuditResult.BLOCKED,
                event_metadata={
                    "bot_id": str(bot_id),
                    "channel": channel,
                    "pattern_type": pattern_type,
                    "input_length": len(sanitized_message)
                }
            )

        return False, sanitized_message, "Invalid characters detected. Please try again."

    return True, sanitized_message, None
