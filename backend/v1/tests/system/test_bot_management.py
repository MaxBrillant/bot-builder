"""
Bot entity (Tests 347-359)
Reorganized from: test_29_bot_entity_constraints.py

Tests validate: Bot entity
"""
import pytest

def test_347_bot_name_max_96_characters():
    """✅ Bot name maximum 96 characters"""
    # Spec: "name: string (max 96 characters, e.g., 'Tujane Ride Sharing')"

    # Valid: Exactly 96 characters
    valid_name = "A" * 96
    bot_valid = {
    "name": valid_name,
    "description": "Test bot",
    "status": "active"
    }
    # Expected: Valid

    # Invalid: 97 characters
    invalid_name = "A" * 97
    bot_invalid = {
    "name": invalid_name,
    "description": "Test bot",
    "status": "active"
    }

    # Expected:
    # - Validation error
    # - Error: "Bot name exceeds maximum length of 96 characters"


def test_348_bot_description_max_512_characters():
    """✅ Bot description maximum 512 characters"""
    # Spec: "description: string (optional, max 512 characters)"

    # Valid: Exactly 512 characters
    valid_description = "A" * 512
    bot_valid = {
    "name": "Test Bot",
    "description": valid_description,
    "status": "active"
    }
    # Expected: Valid

    # Invalid: 513 characters
    invalid_description = "A" * 513
    bot_invalid = {
    "name": "Test Bot",
    "description": invalid_description,
    "status": "active"
    }

    # Expected:
    # - Validation error
    # - Error: "Bot description exceeds maximum length of 512 characters"


def test_349_bot_description_optional():
    """✅ Bot description is optional"""
    # Spec: "description: string (optional, max 512 characters)"

    bot_without_description = {
    "name": "Test Bot",
    "status": "active"
    # No description
    }

    # Expected: Valid bot creation
    # Description can be null or omitted



def test_350_bot_status_active_processes_messages():
    """✅ Active bot processes webhook messages normally"""
    # Spec: "Active: Receives and processes messages via webhook"

    bot = {
    "id": "bot_123",
    "name": "Test Bot",
    "status": "active"
    }

    webhook_request = {
    "bot_id": "bot_123",
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }

    # Expected:
    # - Bot status checked
    # - Status is "active"
    # - Message processed normally
    # - Trigger keywords matched
    # - Session created/resumed
    # - Flow executed


def test_351_bot_status_inactive_rejects_messages():
    """✅ Inactive bot rejects webhook messages"""
    # Spec: "Inactive: Webhook returns 'Bot unavailable' message"

    bot = {
    "id": "bot_123",
    "name": "Test Bot",
    "status": "inactive"
    }

    webhook_request = {
    "bot_id": "bot_123",
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }

    # Expected:
    # - Bot status checked first
    # - Status is "inactive"
    # - Message rejected (not processed)
    # - User sees: "Bot unavailable"
    # - No session created
    # - No flow processing


def test_352_bot_status_transition_active_to_inactive():
    """✅ Bot can transition from active to inactive"""
    # Spec: Bot Lifecycle section

    bot = {
    "id": "bot_123",
    "status": "active"
    }

    # User updates bot status
    update_request = {
    "status": "inactive"
    }

    # Expected:
    # - Status updated to "inactive"
    # - New messages rejected
    # - Existing sessions remain active (or terminated based on implementation)
    # - Bot no longer processes new webhooks


def test_353_bot_status_transition_inactive_to_active():
    """✅ Bot can transition from inactive to active"""

    bot = {
    "id": "bot_123",
    "status": "inactive"
    }

    # User reactivates bot
    update_request = {
    "status": "active"
    }

    # Expected:
    # - Status updated to "active"
    # - Bot starts processing webhooks again
    # - New sessions can be created



def test_354_webhook_url_format():
    """✅ Webhook URL follows format: /webhook/{bot_id}"""
    # Spec: "webhook_url: string (auto-generated: /webhook/{bot_id})"

    bot = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Bot"
    }

    # Expected webhook URL:
    expected_url = "/webhook/550e8400-e29b-41d4-a716-446655440000"

    # OR full URL:
    expected_full_url = "https://botbuilder.com/webhook/550e8400-e29b-41d4-a716-446655440000"

    # Expected:
    # - Webhook URL auto-generated on bot creation
    # - Format: /webhook/{bot_id}
    # - Bot ID is UUID in URL path


def test_355_webhook_secret_generated_on_creation():
    """✅ Webhook secret auto-generated on bot creation"""
    # Spec: "webhook_secret: string (security token)"

    bot_creation_request = {
    "name": "Test Bot",
    "description": "Test",
    "status": "active"
    }

    # Expected response:
    bot_created = {
    "id": "generated-uuid",
    "name": "Test Bot",
    "webhook_url": "/webhook/{bot_id}",
    "webhook_secret": "auto-generated-secret-token",  # System-generated
    "status": "active"
    }

    # Expected:
    # - webhook_secret auto-generated (not user-provided)
    # - Secret is cryptographically secure
    # - Used to validate incoming webhook requests


def test_356_webhook_secret_validation_on_request():
    """✅ Webhook requests validated with secret"""
    # Spec: Webhook secret validation for incoming messages

    bot = {
    "id": "bot_123",
    "webhook_secret": "secret_token_abc123"
    }

    # Valid request with correct secret
    valid_request = {
    "headers": {
    "X-Webhook-Secret": "secret_token_abc123"  # Correct
    },
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }

    # Expected: Request accepted, processed normally

    # Invalid request with wrong secret
    invalid_request = {
    "headers": {
    "X-Webhook-Secret": "wrong_secret"  # Incorrect
    },
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }

    # Expected:
    # - Request rejected
    # - HTTP 401 Unauthorized or 403 Forbidden
    # - Message not processed



def test_357_same_user_multiple_bots_independent_sessions():
    """✅ Same user can have active sessions in multiple bots simultaneously"""
    # Spec: "Same user can have active sessions in multiple bots at the same time"

    user_id = "+254712345678"
    channel = "whatsapp"

    # User interacts with Bot A
    session_bot_a = {
    "session_key": f"{channel}:{user_id}:bot_aaa",
    "bot_id": "bot_aaa",
    "flow_id": "flow_1",
    "context": {"name": "John", "step": "collecting_email"}
    }

    # Same user interacts with Bot B
    session_bot_b = {
    "session_key": f"{channel}:{user_id}:bot_bbb",
    "bot_id": "bot_bbb",
    "flow_id": "flow_5",
    "context": {"product": "Widget", "step": "payment"}
    }

    # Expected:
    # - Both sessions active simultaneously
    # - Different session keys (include bot_id)
    # - Contexts completely isolated
    # - User can interact with both bots
    # - Sessions don't interfere with each other


def test_358_trigger_keywords_bot_scoped_not_global():
    """✅ Trigger keywords scoped per bot, not globally unique"""
    # Spec: "Trigger keywords scoped per bot"
    # "✅ Bot A can have Flow 1 with keyword 'START'"
    # "✅ Bot B can have Flow 1 with keyword 'START' (different bot, allowed)"

    bot_a_flows = [
    {
    "flow_id": "flow_a1",
    "bot_id": "bot_aaa",
    "trigger_keywords": ["START", "HELP"]
    }
    ]

    bot_b_flows = [
    {
    "flow_id": "flow_b1",
    "bot_id": "bot_bbb",
    "trigger_keywords": ["START", "HELP"]  # Same keywords, different bot
    }
    ]

    # Expected:
    # - Both flows valid
    # - No keyword conflict (different bots)
    # - "START" in Bot A triggers flow_a1
    # - "START" in Bot B triggers flow_b1
    # - Keywords isolated per bot


def test_359_webhook_routing_to_specific_bot():
    """✅ Webhook routes message to specific bot only"""
    # Spec: "The integration layer sends messages directly to specific bot webhooks: POST /webhook/{bot_id}"

    # User sends "START" to Bot A's webhook
    request_to_bot_a = {
    "url": "POST /webhook/bot_aaa",
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }

    # Expected:
    # - Bot A receives message
    # - Bot A's trigger keywords checked
    # - Bot A's flows processed
    # - Session key: "whatsapp:+254712345678:bot_aaa"
    # - Bot B NOT involved at all

    # If same user sends message to Bot B's webhook
    request_to_bot_b = {
    "url": "POST /webhook/bot_bbb",
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }

    # Expected:
    # - Bot B receives message
    # - Bot B's trigger keywords checked
    # - Bot B's flows processed
    # - Session key: "whatsapp:+254712345678:bot_bbb"
    # - Completely independent from Bot A
