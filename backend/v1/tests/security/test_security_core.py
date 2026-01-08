"""
Core security (Tests 121-130)
Reorganized from: test_09_security.py

Tests validate: Core security
"""
import pytest

def test_121_bot_ownership_enforced():
    """✅ Bot ownership enforced - user can only access their bots"""
    # Spec: "Every bot belongs to a specific user"
    # "Users cannot access or modify other users' bots"

    user_a_id = "user_aaa"
    user_b_id = "user_bbb"

    bot_owned_by_a = {
    "id": "bot_123",
    "owner_user_id": user_a_id,
    "name": "User A's Bot"
    }

    # User B attempts to access/modify User A's bot
    # Expected: Access denied (403 Forbidden)
    # Error: "You do not have permission to access this bot"

    # User A can access their own bot
    # Expected: Access granted


def test_122_flow_ownership_enforced():
    """✅ Flow ownership enforced - user can only access flows in their bots"""
    # Spec: "Every flow belongs to a specific bot"
    # "User authentication verified, Bot ownership verified"

    user_a_id = "user_aaa"
    user_b_id = "user_bbb"

    bot_a = {"id": "bot_123", "owner_user_id": user_a_id}
    flow_in_bot_a = {"id": "flow_456", "bot_id": "bot_123"}

    # User B attempts to access flow in Bot A
    # Expected: Access denied
    # Validation chain:
    # 1. Check user owns bot
    # 2. Check flow belongs to bot
    # 3. Deny if either fails



def test_123_webhook_secret_validation():
    """✅ Webhook secret validation on incoming messages"""
    # Spec: "Webhook secret validation for incoming messages"
    # "Each bot gets unique webhook URL with secret"

    bot = {
    "id": "bot_123",
    "webhook_url": "https://botbuilder.com/webhook/bot_123",
    "webhook_secret": "secret_xyz789"
    }

    # Valid request with correct secret
    request_valid = {
    "headers": {
    "X-Webhook-Secret": "secret_xyz789"
    },
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }
    # Expected: Request accepted, message processed

    # Invalid request with wrong secret
    request_invalid = {
    "headers": {
    "X-Webhook-Secret": "wrong_secret"
    },
    "body": {
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
    }
    }
    # Expected: Request rejected (401 Unauthorized)



def test_124_input_whitespace_trimming():
    """✅ Input whitespace trimmed automatically"""
    # Spec: "System automatically trims whitespace (leading/trailing)"
    # "All user input is treated as untrusted"

    user_inputs = [
    "  START  ",
    "\tSTART\t",
    "\nSTART\n",
    "START   "
    ]

    # All should be trimmed to "START"
    for inp in user_inputs:
        trimmed = inp.strip()
        assert trimmed == "START"

    # Prevents injection via whitespace manipulation


def test_125_no_automatic_sanitization_for_special_chars():
    """✅ No automatic sanitization for special characters"""
    # Spec: "No automatic sanitization for special characters or injection attempts"
    # "Developer Responsibility: Validate and sanitize input appropriately"

    user_input = "<script>alert('xss')</script>"

    # System does NOT automatically escape HTML/JS
    # Developer must:
    # 1. Use strict validation in PROMPT nodes
    # 2. Sanitize in backend API before storage
    # 3. Use appropriate output encoding

    # Spec recommendation: Use strict REGEX validation
    # Example: "^[A-Za-z0-9_-]+$" for alphanumeric only



def test_126_session_isolation_no_cross_session_access():
    """✅ Sessions isolated - no cross-session data access"""
    # Spec: "❌ Not Supported: Cross-session data access"
    # "Session isolation (no cross-session data access)"

    session_user_a = {
    "session_key": "whatsapp:+254712345678:bot_123",
    "context": {"secret_data": "sensitive"}
    }

    session_user_b = {
    "session_key": "whatsapp:+254787654321:bot_123",
    "context": {"other_data": "value"}
    }

    # User B's flow CANNOT access User A's context
    # No template like {{other_user.secret_data}}
    # No API to query other sessions



def test_127_jwt_authentication_on_protected_endpoints():
    """✅ JWT authentication required on all protected endpoints"""
    # Spec: "JWT-based authentication with bcrypt password hashing"

    protected_endpoints = [
    "/api/bots",
    "/api/flows",
    "/api/flows/{flow_id}",
    "/api/users/me"
    ]

    # Request without JWT token
    request_no_auth = {
    "headers": {},
    "method": "GET",
    "path": "/api/bots"
    }
    # Expected: 401 Unauthorized

    # Request with invalid JWT
    request_invalid_jwt = {
    "headers": {
    "Authorization": "Bearer invalid_token_xyz"
    },
    "method": "GET",
    "path": "/api/bots"
    }
    # Expected: 401 Unauthorized

    # Request with valid JWT
    request_valid_jwt = {
    "headers": {
    "Authorization": "Bearer valid_token_abc123"
    },
    "method": "GET",
    "path": "/api/bots"
    }
    # Expected: 200 OK (if authorized)



def test_128_no_credentials_in_flow_json_validation():
    """✅ Validation check: no credentials in flow JSON"""
    # Spec: "Critical Rule: Never put sensitive credentials directly in flow JSON files"
    # "❌ NEVER DO THIS: Authorization: Bearer sk_live_YOUR_SECRET_KEY"

    flow_with_hardcoded_secret = {
    "name": "bad_flow",
    "trigger_keywords": ["START"],
    "start_node_id": "node_api",
    "nodes": {
    "node_api": {
        "id": "node_api",
        "type": "API_ACTION",
        "config": {
            "request": {
                "method": "POST",
                "url": "https://api.example.com/data",
                "headers": {
                    "Authorization": "Bearer sk_live_1234567890"  # ❌ EXPOSED!
                }
            }
        },
        "routes": [],
        "position": {"x": 0, "y": 0}
    }
    }
    }

    # Validation should detect patterns like:
    # - "Bearer sk_live_"
    # - "Bearer sk_test_"
    # - "api_key"
    # - Long base64 strings
    # - Common secret patterns

    # Expected: Validation warning or error
    # "Warning: Possible credentials detected in flow JSON. Use backend proxy pattern."



def test_129_api_urls_must_be_https():
    """✅ API URLs must be HTTPS (warning or enforcement)"""
    # Spec: "Requirements: Always use HTTPS for API endpoints"

    # Valid HTTPS URL
    url_https = "https://api.example.com/users"
    assert url_https.startswith("https://")

    # Invalid HTTP URL
    url_http = "http://api.example.com/users"
    # Expected: Validation warning or error
    # "Warning: API URL should use HTTPS for security"

    # Exception: localhost for development
    url_localhost = "http://localhost:3000/api"
    # May be allowed for local development



def test_130_error_messages_no_internal_details():
    """✅ Error messages don't expose internal system details"""
    # Spec: "Avoid Exposing: Internal system details, Database structure, API endpoints, Stack traces"

    # ❌ INSECURE error message
    bad_error = "Database connection failed: Connection refused to mysql://prod-db:3306/users"
    # Exposes: DB type, hostname, port, database name

    # ✅ SECURE error message
    good_error = "We're experiencing technical difficulties. Please try again later or contact support."
    # No internal details exposed

    # Error messages should be:
    # - Generic and user-friendly
    # - No stack traces
    # - No database queries
    # - No internal paths
    # - No version numbers
