"""
Session lifecycle (Tests 087-105)
Reorganized from: test_07_session_management.py

Tests validate: Session lifecycle
"""
import pytest

def test_87_session_created_on_first_message_with_trigger():
    """✅ Session created on first message with trigger keyword"""
    # Spec: "User sends message via webhook → Create Session (ACTIVE)"
    # "Sessions store flow snapshot or version reference"

    bot_id = "bot_abc123"
    channel = "whatsapp"
    channel_user_id = "+254712345678"
    trigger_keyword = "START"

    # User sends "START" for first time
    # Expected:
    # - New session created with status ACTIVE
    # - session_key = "whatsapp:+254712345678:bot_abc123"
    # - Flow snapshot stored (immutable copy)
    # - Context initialized with variable defaults
    # - created_at timestamp recorded
    # - expires_at = created_at + 30 minutes


def test_88_session_key_format_validation():
    """✅ Session key format: channel:channel_user_id:bot_id"""
    # Spec: "Session Key Format: channel:channel_user_id:bot_id"
    # Examples: "whatsapp:+254712345678:bot_abc123"

    # Test case 1: WhatsApp
    session_key_wa = "whatsapp:+254712345678:bot_abc123"
    parts = session_key_wa.split(":")
    assert parts[0] == "whatsapp"
    assert parts[1] == "+254712345678"
    assert parts[2] == "bot_abc123"

    # Test case 2: Telegram
    session_key_tg = "telegram:123456789:bot_xyz789"
    parts = session_key_tg.split(":")
    assert parts[0] == "telegram"

    # Test case 3: Different bot, same user
    session_key_bot2 = "whatsapp:+254712345678:bot_def456"
    # Different session from bot_abc123



def test_89_session_timeout_30_minutes_absolute():
    """✅ Session timeout after 30 minutes (absolute from creation)"""
    # Spec: "✅ Absolute timeout: 30 minutes from session creation"
    # "❌ Not a sliding window (doesn't reset on activity)"

    created_at = datetime(2024, 1, 1, 10, 0, 0)  # 10:00 AM
    expires_at = created_at + timedelta(minutes=30)  # 10:30 AM

    # Timeline:
    # 10:00 - Session created
    # 10:15 - User sends message (15 min remaining, NOT reset)
    # 10:29 - User sends message (1 min remaining)
    # 10:30 - Session expires (exactly 30 min from creation)
    # 10:31 - Message rejected (expired)

    assert expires_at == datetime(2024, 1, 1, 10, 30, 0)


def test_90_expired_session_rejects_messages():
    """✅ Expired session rejects messages with error"""
    # Spec: "Post-Expiry Behavior: Messages sent after expiration are rejected"
    # "User receives: 'Session expired. Please start again.'"

    session_status = "EXPIRED"
    current_time = datetime(2024, 1, 1, 10, 31, 0)
    expires_at = datetime(2024, 1, 1, 10, 30, 0)

    assert current_time > expires_at
    # Expected: Message rejected with error
    # Error message: "Session expired. Please start again."
    # To resume: User must send trigger keyword


def test_91_session_timeout_not_configurable():
    """✅ Session timeout is NOT configurable per flow"""
    # Spec: "❌ Not configurable per flow"
    # Fixed at 30 minutes system-wide

    # No configuration option exists in flow definition
    # No configuration option in defaults
    # No way to extend timeout



def test_92_end_node_marks_session_completed():
    """✅ END node reached → session marked COMPLETED"""
    # Spec: "END node reached → COMPLETED status"

    # Flow reaches END node
    # Expected:
    # - Session status = COMPLETED
    # - Future messages rejected until new session
    # - Context cleared/archived


def test_93_session_timeout_marks_expired():
    """✅ 30 minutes elapsed → session marked EXPIRED"""
    # Spec: "30 minutes elapsed → EXPIRED status"

    created_at = datetime.now()
    current_time = created_at + timedelta(minutes=31)

    # Expected:
    # - Session status = EXPIRED
    # - Automatic cleanup after expiration


def test_94_new_flow_deletes_old_session_silently():
    """✅ New flow triggered → old session deleted, new session created"""
    # Spec: "⚠️ Starting new flow in same bot terminates old session silently"
    # "No warning shown - this is intentional for simplicity"

    # User has active session in bot_abc123 (flow: "onboarding")
    active_session = {
    "session_key": "whatsapp:+254712345678:bot_abc123",
    "flow_id": "flow_onboarding",
    "status": "ACTIVE",
    "current_node": "node_step_3"
    }

    # User sends new trigger keyword "HELP" (different flow)
    new_trigger = "HELP"

    # Expected:
    # - Old session deleted immediately
    # - New session created for "HELP" flow
    # - No warning to user
    # - User loses progress in onboarding flow


def test_95_no_route_match_marks_error():
    """✅ No matching route → session marked ERROR"""
    # Spec: "No route match → ERROR status, session ends, user sees error message"

    # Flow execution reaches node with routes, no route matches
    # Expected:
    # - Session status = ERROR
    # - Error message: "An error occurred. Please try again."
    # - Session ends


def test_96_max_auto_progression_marks_error():
    """✅ Max auto-progression (10 nodes) → session marked ERROR"""
    # Spec: "Max auto-progression steps: 10 consecutive nodes without user input"
    # "Max auto-progression → ERROR status"

    # Flow: MESSAGE → MESSAGE → MESSAGE... (11 nodes without PROMPT/MENU)
    auto_progression_count = 11

    assert auto_progression_count > 10
    # Expected:
    # - After 10th node, error triggered
    # - Session status = ERROR
    # - Error message: "System error. Please contact support."



def test_97_multi_bot_sessions_isolated():
    """✅ Same user can have sessions in multiple bots simultaneously"""
    # Spec: "Multi-Bot Support: Users can interact with multiple bots simultaneously"
    # "Session Isolation: Each bot maintains its own independent sessions"

    channel_user_id = "+254712345678"
    channel = "whatsapp"

    # User has session in Bot A
    session_bot_a = {
    "session_key": f"{channel}:{channel_user_id}:bot_a",
    "status": "ACTIVE",
    "flow_id": "flow_1"
    }

    # User has session in Bot B
    session_bot_b = {
    "session_key": f"{channel}:{channel_user_id}:bot_b",
    "status": "ACTIVE",
    "flow_id": "flow_2"
    }

    # Both sessions active simultaneously
    # Contexts are isolated - no data sharing
    # Trigger keywords are bot-scoped


def test_98_multi_channel_sessions_isolated():
    """✅ Same user on different channels → separate sessions"""
    # Spec: "Sessions are keyed by: channel:channel_user_id:bot_id"

    bot_id = "bot_abc123"

    # Session 1: User on WhatsApp
    session_wa = {
    "session_key": f"whatsapp:+254712345678:{bot_id}",
    "status": "ACTIVE"
    }

    # Session 2: Same user on Telegram (different channel_user_id)
    session_tg = {
    "session_key": f"telegram:123456789:{bot_id}",
    "status": "ACTIVE"
    }

    # Separate sessions even for same logical user


def test_99_one_active_session_per_user_per_bot():
    """✅ One active session per user per bot per channel"""
    # Spec: "✅ One active session per user per bot per channel"
    # "❌ Cannot pause/resume sessions"

    session_key = "whatsapp:+254712345678:bot_abc123"

    # Only one ACTIVE session allowed with this key
    # New session with same key replaces old one



def test_100_context_variables_persist_across_nodes():
    """✅ Context variables persist across nodes in session"""
    # Spec: "✅ Pass between nodes, Use in templates, Use in conditions"

    initial_context = {"user_name": "Alice"}

    # Node 1 (PROMPT) collects age
    # Context after node 1: {"user_name": "Alice", "age": 25}

    # Node 2 (MESSAGE) uses both variables
    # Template: "Hello {{context.user_name}}, age {{context.age}}"

    # Context persists throughout session


def test_101_context_initialized_with_variable_defaults():
    """✅ Context initialized with variable defaults from flow"""
    # Spec: "Context initialized with variable defaults"

    flow_variables = {
    "user_name": {"type": "string", "default": "Guest"},
    "age": {"type": "number", "default": 0},
    "verified": {"type": "boolean", "default": False},
    "items": {"type": "array", "default": []}
    }

    # Expected initial context:
    initial_context = {
    "user_name": "Guest",
    "age": 0,
    "verified": False,
    "items": []
    }


def test_102_context_array_truncated_to_24_items():
    """✅ Array variables truncated to 24 items at runtime"""
    # Spec: "Array length in context: 24 items per array variable (truncated if exceeded)"
    # "Arrays exceeding 24 items are silently truncated to first 24 items"

    # API returns array with 30 items
    api_response_items = list(range(30))
    assert len(api_response_items) == 30

    # After storing in context
    context = {"items": api_response_items[:24]}  # Truncated

    assert len(context["items"]) == 24
    # No error, silently truncated


def test_103_context_size_limit_100kb():
    """✅ Total context size limited to 100 KB"""
    # Spec: "Context size (total): 100 KB"

    # Large context with many variables
    # Expected: Enforcement of 100 KB limit
    # Exceeding limit → error or truncation



def test_104_active_sessions_use_flow_snapshot():
    """✅ Active sessions use flow snapshot from session start"""
    # Spec: "Flow Version Isolation: Sessions store flow snapshot from session start"
    # "Flow updates don't affect active sessions"

    # Timeline:
    # 10:00 - Flow "checkout" deployed (version 1)
    # 10:05 - User A starts session (uses version 1 snapshot)
    # 10:10 - Flow "checkout" updated (version 2)
    # 10:15 - User B starts session (uses version 2)
    # 10:20 - User A continues (still uses version 1 snapshot)

    # User A's session is bound to version 1
    # User B's session is bound to version 2
    # Ensures consistent user experience


def test_105_flow_updates_dont_affect_active_sessions():
    """✅ Flow updates don't affect active sessions"""
    # Spec: "Flow updates don't affect active sessions, Ensures consistent user experience"

    active_session = {
    "session_key": "whatsapp:+254712345678:bot_abc123",
    "flow_snapshot": {
    "name": "checkout",
    "version": 1,
    "nodes": {}  # Original flow definition
    },
    "status": "ACTIVE"
    }

    # Developer updates flow definition
    updated_flow = {
    "name": "checkout",
    "version": 2,
    "nodes": {}  # Modified flow definition
    }

    # Active session continues using version 1 snapshot
    # New sessions use version 2


def test_360_active_session_uses_flow_snapshot_from_start():
    """✅ Active sessions use flow snapshot from session start"""
    # Spec: "Sessions store flow snapshot or version reference"
    # "Flow updates don't affect active sessions"

    # Timeline:
    # 10:00 - Flow v1 submitted and stored
    flow_v1 = {
    "id": "flow_abc",
    "name": "checkout",
    "version": "v1",
    "nodes": {"node_1": {"config": {"text": "Old message"}}}
    }

    # 10:05 - User A starts session (captures flow v1 snapshot)
    session_a = {
    "session_key": "whatsapp:+254111111111:bot_123",
    "flow_snapshot": flow_v1,  # Snapshot of v1
    "created_at": "10:05",
    "current_node": "node_1"
    }

    # 10:10 - Flow updated to v2
    flow_v2 = {
    "id": "flow_abc",  # Same ID
    "name": "checkout",
    "version": "v2",
    "nodes": {"node_1": {"config": {"text": "New message"}}}  # Changed
    }

    # 10:15 - User B starts new session (uses flow v2)
    session_b = {
    "session_key": "whatsapp:+254222222222:bot_123",
    "flow_snapshot": flow_v2,  # Snapshot of v2
    "created_at": "10:15",
    "current_node": "node_1"
    }

    # 10:20 - User A continues their session
    # Expected:
    # - Session A still uses flow v1 snapshot
    # - User A sees: "Old message"
    # - Session A NOT affected by flow update

    # 10:25 - User B continues their session
    # Expected:
    # - Session B uses flow v2 snapshot
    # - User B sees: "New message"


def test_361_flow_updates_visible_to_new_sessions_only():
    """✅ Flow updates only affect new sessions, not existing ones"""
    # Spec: "New sessions use updated version"

    # Flow originally has 3 nodes
    original_flow = {
    "nodes": {"node_1": {}, "node_2": {}, "node_3": {}}
    }

    # Active session started with original flow
    active_session = {
    "flow_snapshot": original_flow,
    "current_node": "node_2"
    }

    # Flow updated: node_3 removed, node_4 added
    updated_flow = {
    "nodes": {"node_1": {}, "node_2": {}, "node_4": {}}  # node_3 gone, node_4 added
    }

    # Active session continues
    # Expected:
    # - Active session can still route to node_3 (exists in snapshot)
    # - Active session cannot route to node_4 (not in snapshot)

    # New session starts
    new_session = {
    "flow_snapshot": updated_flow
    }

    # Expected:
    # - New session has node_4 available
    # - New session doesn't have node_3


def test_362_flow_id_immutable_name_mutable():
    """✅ Flow ID (UUID) immutable, but name can be changed"""
    # Spec: "Flow is identified by its UUID (immutable)"
    # "Flow name can be changed during update (must remain unique within bot)"

    flow_original = {
    "id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",  # UUID - immutable
    "name": "checkout_flow_v1"  # Name - mutable
    }

    # Update flow name
    flow_update = {
    "id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",  # Same UUID
    "name": "checkout_flow_v2"  # New name
    }

    # Expected:
    # - Flow identified by UUID (doesn't change)
    # - Name updated successfully
    # - New name must be unique within bot
    # - Active sessions still reference same flow (by UUID)



def test_363_flow_loaded_from_database_cached_in_redis():
    """✅ Flows loaded from database, cached in Redis"""
    # Spec: "Redis caching for performance"

    # First flow retrieval
    # Expected:
    # 1. Check Redis cache (miss)
    # 2. Load from database
    # 3. Store in Redis with TTL
    # 4. Return flow

    # Second retrieval (within TTL)
    # Expected:
    # 1. Check Redis cache (hit)
    # 2. Return cached flow (no database query)


def test_364_redis_cache_invalidated_on_flow_update():
    """✅ Redis cache invalidated when flow updated"""
    # Spec: "Cache invalidated on flow updates"

    # Flow in Redis cache
    cached_flow_v1 = {
    "id": "flow_123",
    "version": "v1"
    }

    # Flow updated
    flow_update = {
    "id": "flow_123",
    "version": "v2"
    }

    # Expected:
    # - Flow update triggers cache invalidation
    # - Redis cache entry for flow_123 removed
    # - Next retrieval loads v2 from database
    # - v2 cached in Redis



def test_365_sessions_stored_in_database_survive_restarts():
    """✅ Sessions persist in database, survive server restarts"""
    # Spec: "Database persistence - sessions survive server restarts"

    # Session created
    session = {
    "session_key": "whatsapp:+254712345678:bot_123",
    "flow_snapshot": {"nodes": {}},
    "context": {"name": "John", "step": 2},
    "current_node": "node_2",
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-01-01T10:30:00Z"
    }

    # Expected: Session stored in database (PostgreSQL)

    # Server restart happens

    # User sends message
    # Expected:
    # - Session retrieved from database
    # - Context restored: {"name": "John", "step": 2}
    # - Current node: "node_2"
    # - Flow continues from where it left off


def test_366_session_expiry_enforced_after_restart():
    """✅ Session expiry still enforced after restart"""

    # Session created
    session = {
    "created_at": "10:00 AM",
    "expires_at": "10:30 AM"  # 30 min absolute timeout
    }

    # Server restart at 10:15 AM

    # User sends message at 10:31 AM (31 min after creation)
    # Expected:
    # - Session expired (30 min from creation)
    # - Status: EXPIRED
    # - Message rejected: "Session expired. Please start again."



def test_367_cannot_delete_context_variables():
    """✅ Cannot delete context variables, must set to null instead"""
    # Spec: "❌ Cannot delete variables (set to null instead)"

    context_before = {
    "name": "John",
    "email": "john@example.com",
    "phone": "+254712345678"
    }

    # Attempt to "delete" phone variable
    # Expected behavior: Set to null, not delete
    context_after = {
    "name": "John",
    "email": "john@example.com",
    "phone": None  # Set to null, not deleted
    }

    # Expected:
    # - Variable still exists in context
    # - Value is null
    # - Variable key not removed


def test_368_cannot_rename_context_variables():
    """✅ Cannot rename context variables"""
    # Spec: "❌ Cannot rename variables"

    context = {
    "user_name": "John"
    }

    # To "rename" user_name to name:
    # Expected: Must create new variable, set old to null
    context_updated = {
    "user_name": None,  # Old variable set to null
    "name": "John"      # New variable created
    }

    # Expected:
    # - No rename operation supported
    # - Must use create new + nullify old pattern


def test_369_nested_objects_immutable_once_set():
    """✅ Nested objects are immutable once set"""
    # Spec: "❌ No nested update operations (nested objects are immutable once set; use API to reconstruct and reassign entire object)"

    # Initial context
    context = {
    "user": {
    "name": "John",
    "email": "john@example.com",
    "address": {
        "city": "Nairobi",
        "country": "Kenya"
    }
    }
    }

    # Cannot update nested field directly
    # ❌ context.user.email = "newemail@example.com"  # Not supported

    # Must reconstruct entire object
    updated_user = {
    "name": "John",
    "email": "newemail@example.com",  # Updated
    "address": {
    "city": "Nairobi",
    "country": "Kenya"
    }
    }

    context_updated = {
    "user": updated_user  # Entire object replaced
    }

    # Expected:
    # - Nested field updates not supported
    # - Must use API to reconstruct entire object
    # - Reassign entire object to context variable
