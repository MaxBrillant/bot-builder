# Session Management

Comprehensive documentation of Bot Builder's conversation session system.

## Overview

Sessions manage conversation state for users interacting with bots. Each session tracks:
- Current position in flow execution (current_node_id)
- User context variables (encrypted)
- Flow snapshot for version isolation (encrypted, immutable)
- Lifecycle status and timeout enforcement
- Auto-progression and validation attempt tracking

**Source Files:**
- `/backend/v1/app/core/session_manager.py` (701 lines) - lifecycle operations
- `/backend/v1/app/models/session.py` (251 lines) - data model
- `/backend/v1/app/core/redis_manager.py` (728 lines) - session caching

## Session Key Format

**Composite Key:** `channel:channel_user_id:bot_id`

| Component | Description | Example |
|-----------|-------------|---------|
| `channel` | Communication platform | `WHATSAPP`, `TELEGRAM`, `SMS` |
| `channel_user_id` | Platform-specific user ID | Phone number, Telegram ID, etc. |
| `bot_id` | Bot UUID | `550e8400-e29b-41d4-a716-446655440000` |

**Uniqueness Constraint:** Only ONE active session per (channel, channel_user_id, bot_id) tuple.
- Database: `idx_unique_active_session` partial unique index (WHERE status = 'ACTIVE')
- Redis: `session:active:{channel}:{channel_user_id}:{bot_id}`

**Code Reference:** `Session.session_key` property (session.py:184-197)

## Lifecycle States

| Status | Description | Terminal | Terminal Timestamp |
|--------|-------------|----------|-------------------|
| `ACTIVE` | Conversation in progress | No | N/A |
| `COMPLETED` | Flow reached END node | Yes | `completed_at` set |
| `EXPIRED` | 30-minute timeout exceeded | Yes | `completed_at` set |
| `ERROR` | Max auto-progression or system error | Yes | `completed_at` set |

**State Transitions:**
```
ACTIVE → COMPLETED  (END node reached)
ACTIVE → EXPIRED    (timeout exceeded)
ACTIVE → ERROR      (max auto-progression, critical error)
```

**Code References:**
- Status enum: `app/utils/constants/enums.py` (SessionStatus)
- Transition methods: `session_manager.py:448-531` (complete/expire/error)
- Model check methods: `session.py:230-251` (is_expired, is_active, mark_*)

## Session Creation

**Method:** `SessionManager.create_session()` (session_manager.py:52-209)

**Operation:** Atomic termination + creation with SELECT FOR UPDATE lock

**Steps:**
1. Lock existing ACTIVE session for (channel, channel_user_id, bot_id)
2. If existing session found → DELETE (silent termination)
3. Create new session with:
   - `created_at` = now
   - `expires_at` = created_at + 30 minutes (absolute)
   - `status` = ACTIVE
   - `auto_progression_count` = 0
   - `validation_attempts` = 0
   - `current_node_id` = flow_snapshot.start_node_id
   - `context` = initialized from flow variables + defaults
4. Commit transaction (releases lock)
5. Log audit event: `session_created`

**Race Condition Handling:**
- Max 2 retry attempts on `idx_unique_active_session` violation
- Lock held throughout delete+create (prevents concurrent creation)
- Uses NOWAIT on get operations to fail fast if locked

**Silent Termination:**
When a new flow starts, any existing active session is deleted without warning.
- Audit log: `session_terminated_on_new_flow`
- No user notification
- Previous session context lost

**Code Reference:** session_manager.py:52-209

## Session Resumption

**Method:** `SessionManager.get_active_session()` (session_manager.py:211-255)

**Locking Modes:**
| Parameter | Lock Type | Use Case | Failure Behavior |
|-----------|-----------|----------|------------------|
| `for_update=False` | No lock | Read-only operations | None |
| `for_update=True` | SELECT FOR UPDATE NOWAIT | Modify session state | Raises `SessionLockError` |

**NOWAIT Behavior:**
- Fails immediately if row locked by another request
- Prevents queue buildup on concurrent user messages
- Returns `SessionLockError`: "Session is being processed by another request"

**Timeout Check:**
After retrieval, engine checks `SessionManager.check_timeout()`:
- Returns `True` if `datetime.now(utc) > expires_at`
- Timeout is absolute (30 minutes from creation), not sliding window
- Engine calls `expire_session()` and halts execution

**Code References:**
- Get method: session_manager.py:211-255
- Timeout check: session_manager.py:560-576
- Engine timeout handling: app/core/engine.py (process_message)

## Session Update Operations

**Purpose:** Methods for modifying session state during flow execution.

### get_session_by_id()

**Method:** `SessionManager.get_session_by_id(session_id)` (session_manager.py:257-269)

**Purpose:** Retrieve a session by its UUID (no locking).

**Returns:** Session instance or None if not found

**Usage:** Internal helper for session lookups when locking is not required.

**Code Reference:** session_manager.py:257-269

### update_node()

**Method:** `SessionManager.update_node(session_id, node_id)` (session_manager.py:320-338)

**Purpose:** Update the current_node_id on a session to move to the next node in the flow.

**Parameters:**
- `session_id`: Session UUID
- `node_id`: New current node ID

**Transaction Handling:** Does NOT commit - caller's transaction handles commit.

**Usage:** Called by engine during flow execution to track current position.

**Code Reference:** session_manager.py:320-338

### update_context()

**Method:** `SessionManager.update_context(session_id, context)` (session_manager.py:271-318)

**Purpose:** Update session context variables with size validation and array truncation.

**Parameters:**
- `session_id`: Session UUID
- `context`: New context dictionary

**Validation:**
- Max size: 100 KB (UTF-8 encoded JSON)
- Arrays truncated to 24 items (silent)

**Raises:** `ContextSizeExceededError` if size limit exceeded

**Transaction Handling:** Does NOT commit - caller's transaction handles commit.

**Code Reference:** session_manager.py:271-318

### update_session_state()

**Method:** `SessionManager.update_session_state(session_id, node_id, context)` (session_manager.py:609-668)

**Purpose:** Atomic update of both current_node_id and context in a single operation.

**Parameters:**
- `session_id`: Session UUID
- `node_id`: New current node ID
- `context`: New context dictionary

**Validation:** Same as update_context() (size and array truncation)

**Raises:** `ContextSizeExceededError` if size limit exceeded

**Transaction Handling:** Does NOT commit - caller's transaction handles commit.

**Usage:** Preferred method for updating node + context together (more efficient than separate calls).

**Code Reference:** session_manager.py:609-668

## Timeout Rules

| Setting | Value | Type |
|---------|-------|------|
| Duration | 30 minutes | Absolute (not sliding) |
| Calculated | `created_at + timedelta(minutes=30)` | UTC |
| Grace Period (cleanup) | 5 seconds | Prevents premature expiration |

**Enforcement:**
1. **Per-message check:** Engine checks timeout before processing (session_manager.check_timeout)
2. **Background cleanup:** `cleanup_expired_sessions()` marks stale sessions as EXPIRED
   - Runs periodically via background task
   - Query: `WHERE status = 'ACTIVE' AND expires_at < (now - 5 seconds)`
   - Sets `status = EXPIRED`, `completed_at = now`

**Not Sliding:**
Timeout does NOT refresh on user activity. Timer starts at session creation and is immutable.

**Code References:**
- Expiration calculation: session_manager.py:130-132
- Timeout check: session_manager.py:560-576
- Cleanup task: session_manager.py:578-607
- Index for cleanup: session.py:105-108 (idx_sessions_expires)

## Message History

**Field:** `Session.message_history` (JSONB array, default [])

**Note:** Message history is stored as plain JSONB — it is **not encrypted**, unlike `context` and `flow_snapshot`. This is a deliberate choice for query/debugging access, but means message content is visible in the database.

**Purpose:** Stores conversation message log with timestamps for debugging and audit purposes.

**Entry Structure:**
```json
{
  "timestamp": "2024-03-25T10:30:00.000Z",
  "sender": "user|bot|system",
  "message": "message text",
  "node_id": "node_abc123",
  "node_type": "PROMPT" // optional, bot messages only
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 string | UTC timestamp when message was logged |
| `sender` | string | Message source: "user", "bot", or "system" |
| `message` | string | Message text content |
| `node_id` | string | Node ID where message occurred |
| `node_type` | string (optional) | Node type for bot messages (e.g., "PROMPT", "MENU") |

**Size Limit:**
- Automatically truncated to last 50 entries
- Truncation occurs after each message append (engine.py:307-308)
- Oldest messages removed when limit exceeded

**Updates:**
Message history updated by ConversationOrchestrator:
1. User messages logged when received (before processing)
2. Bot messages logged when sent (after node processing)
3. System messages logged on errors (e.g., "no_route_match")

**Not Encrypted:**
Unlike context and flow_snapshot, message_history is stored as plaintext JSONB (for query/analysis).

**Code References:**
- Column definition: session.py:89
- Update logic: engine.py:274-308 (_update_message_history)
- User message logging: engine.py:447-449
- Bot message logging: engine.py:544-547
- System message logging: engine.py:578-582

## Context Storage

**Field:** `Session.context` (encrypted JSONB → LargeBinary)

**Encryption:**
- Physical column: `_context_encrypted` (LargeBinary)
- Hybrid property: `context` (transparent encrypt/decrypt)
- Service: `app.utils.encryption.get_encryption_service()`
- Algorithm: AES-256-GCM (via settings.encryption_key)

**Contents:**
| Key | Purpose | Managed By |
|-----|---------|------------|
| User variables | Flow variables set by PROMPT/MENU/API_ACTION | Processors |
| `_flow_variables` | Variable type definitions (used by `render_json_value()` for type-aware rendering and `_get_variable_type()` for type conversion) | Session initialization |
| `_flow_defaults` | Flow defaults including `retry_logic` config (used by RetryHandler for max_attempts, fail_route, counter_text) | Session initialization |

**Initialization:**
Context populated at session creation from `flow_snapshot`:
```python
# session_manager.py:670-702
context = {}
variables = flow_snapshot.get('variables', {})
for var_name, var_def in variables.items():
    context[var_name] = var_def.get('default')
context['_flow_variables'] = variables
context['_flow_defaults'] = flow_snapshot.get('defaults', {})
```

**Size Constraints:**
- Max context size: 100 KB (UTF-8 encoded JSON)
- Validation: `update_context()` and `update_session_state()` check size before saving
- Exception: `ContextSizeExceededError` if limit exceeded

**Array Truncation:**
Arrays exceeding 24 items are silently truncated to first 24 items when writing to context.
- Enforcement: `_truncate_arrays()` called before all context writes
- Silent operation: No error raised, only debug log
- Spec reference: "All arrays written to context are enforced to 24 items max"

**Updates:**
Context updated via:
1. `update_context(session_id, context)` - context only
2. `update_session_state(session_id, node_id, context)` - atomic node+context update

**Important:** Update methods do NOT commit - caller's transaction handles commit.

**Code References:**
- Hybrid property: session.py:148-165
- Initialization: session_manager.py:670-702
- Size validation: session_manager.py:271-318, 609-668
- Array truncation: session_manager.py:533-558
- Encryption: app/utils/encryption.py

## Flow Snapshot

**Field:** `Session.flow_snapshot` (encrypted JSONB → LargeBinary)

**Purpose:** Version isolation - session executes against flow definition at creation time, immune to flow edits.

**Encryption:**
- Physical column: `_flow_snapshot_encrypted` (LargeBinary)
- Hybrid property: `flow_snapshot` (transparent encrypt/decrypt)
- Same encryption service as context

**Immutability:**
Enforced by `__setattr__` override (session.py:167-178):
```python
def __setattr__(self, name, value):
    if name == 'flow_snapshot':
        encrypted = self.__dict__.get('_flow_snapshot_encrypted')
        if isinstance(encrypted, (bytes, str)):
            current = self.flow_snapshot
            if current is not None and value != current:
                raise ValueError("flow_snapshot is immutable")
    super().__setattr__(name, value)
```

**Contents:**
Complete flow definition at session start:
- `start_node_id` - entry point
- `nodes` - all node configs
- `variables` - flow variable definitions
- `defaults` - retry messages, etc.
- `name`, `bot_id` - metadata

**Why Encrypted:**
Flow definitions may contain sensitive data (API endpoints, business logic, external service URLs).

**Code References:**
- Hybrid property: session.py:130-146
- Immutability enforcement: session.py:167-178
- Creation: session_manager.py:59 (passed as arg), 135-150 (stored)

## Auto-Progression Tracking

**Counter:** `Session.auto_progression_count` (integer, default 0)

**Purpose:** Prevent infinite loops in flows with consecutive non-input nodes.

**Limit:** 10 consecutive nodes without user input (SystemConstraints.MAX_AUTO_PROGRESSION)

**Increment:** Called by engine for nodes that do NOT wait for input:
- `increment_auto_progression(session_id)` → new_count
- Atomic SQL increment: `auto_progression_count = auto_progression_count + 1`
- Raises `MaxAutoProgressionError` if limit exceeded
- On limit exceeded: marks session as ERROR

**Reset:** Called by engine at nodes that DO wait for input (PROMPT, MENU):
- `reset_auto_progression(session_id)` → sets counter to 0

**Example Flow:**
```
START → ACTION (1) → CONDITION (2) → ACTION (3) → PROMPT (reset to 0) → ACTION (1) → END
```

**Transaction Handling:**
Methods do NOT commit - caller's transaction handles commit (prevents session detachment during flow execution loop).

**Code References:**
- Increment: session_manager.py:340-378
- Reset: session_manager.py:380-397
- Limit constant: app/utils/constants/constraints.py (SystemConstraints.MAX_AUTO_PROGRESSION = 10)

## Validation Attempt Tracking

**Counter:** `Session.validation_attempts` (integer, default 0)

**Purpose:** Track retry attempts for failed validations at PROMPT/MENU nodes.

**Operations:**
| Method | Action | Use Case |
|--------|--------|----------|
| `increment_validation_attempts()` | `validation_attempts + 1` | User input failed validation |
| `reset_validation_attempts()` | `validation_attempts = 0` | User input passed validation |

**Atomicity:**
- `increment_validation_attempts()` is NOT atomic - fetches session first, then updates counter (unlike `increment_auto_progression()` which uses SQL atomic increment)
- `reset_validation_attempts()` uses direct SQL update

**No Limit Enforcement:**
SessionManager does not enforce a max validation attempts limit. Processors may implement retry limits based on `_flow_defaults.validation_retry_limit`.

**Transaction Handling:**
Methods do NOT commit - caller's transaction handles commit.

**Code References:**
- Increment: session_manager.py:399-427
- Reset: session_manager.py:429-446

## Redis Caching

**Key Format:** `session:active:{channel}:{channel_user_id}:{bot_id}`

**TTL:** 1800 seconds (30 minutes, matches session timeout)

**Operations:**
| Method | Redis Key | Purpose |
|--------|-----------|---------|
| `cache_session()` | `session:active:...` | Store session data after DB write |
| `get_cached_session()` | `session:active:...` | Fast lookup before DB query |
| `invalidate_session_cache()` | DELETE `session:active:...` | Clear stale cache |

**Failure Policy:** FAIL-OPEN (graceful degradation)
- If Redis unavailable: returns None, falls back to database
- Cache operations log warnings but do not raise exceptions
- Session operations continue without cache

**What's Cached:**
Serialized session data (session.to_dict()):
- session_id, channel, channel_user_id, bot_id
- flow_id, current_node_id
- context (decrypted), status
- created_at, expires_at, completed_at
- auto_progression_count, validation_attempts

**NOT cached:** `flow_snapshot` (too large, rarely needed)

**Code References:**
- Cache ops: redis_manager.py:440-525
- Key format: redis_manager.py:462, 493, 521
- Session serialization: session.py:199-228 (to_dict)

## Cleanup Operations

**Background Task:** `SessionManager.cleanup_expired_sessions()` (session_manager.py:578-607)

**Query:**
```sql
UPDATE sessions
SET status = 'EXPIRED', completed_at = NOW()
WHERE status = 'ACTIVE'
  AND expires_at < NOW() - INTERVAL '5 seconds'
```

**Grace Period:** 5 seconds prevents marking newly created sessions that haven't been committed yet.

**Frequency:** Should be called periodically (e.g., every 5 minutes via background task scheduler).

**Returns:** Count of expired sessions

**Index:** `idx_sessions_expires` partial index on `expires_at WHERE status = 'ACTIVE'` (session.py:105-108)

**Completed Session Cleanup:**
Old completed sessions (COMPLETED, EXPIRED, ERROR) may be archived or deleted by separate cleanup tasks using `idx_sessions_completed_at` index (session.py:117-120).

**Code Reference:** session_manager.py:578-607

## Database Schema

**Table:** `sessions`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `session_id` | UUID | No | uuid4() | Primary key |
| `channel` | VARCHAR(50) | No | - | Part of unique constraint |
| `channel_user_id` | VARCHAR(255) | No | - | Indexed, plaintext (for queries) |
| `bot_id` | UUID | No | - | Foreign key to bots (CASCADE) |
| `flow_id` | UUID | No | - | Foreign key to flows (CASCADE) |
| `_flow_snapshot_encrypted` | BYTEA | No | - | Encrypted JSONB → bytes |
| `current_node_id` | VARCHAR(96) | No | - | Current position in flow |
| `_context_encrypted` | BYTEA | No | - | Encrypted JSONB → bytes |
| `status` | VARCHAR(20) | No | 'ACTIVE' | CHECK constraint |
| `created_at` | TIMESTAMPTZ | No | now() | Session start |
| `expires_at` | TIMESTAMPTZ | No | - | Absolute timeout |
| `completed_at` | TIMESTAMPTZ | Yes | NULL | Terminal timestamp |
| `auto_progression_count` | INTEGER | No | 0 | Max 10 |
| `validation_attempts` | INTEGER | No | 0 | No max enforced |
| `message_history` | JSONB | No | '[]' | Conversation log (truncated to last 50 entries) |

**Indexes:**
| Name | Columns | Type | Condition |
|------|---------|------|-----------|
| `idx_unique_active_session` | (channel, channel_user_id, bot_id) | UNIQUE | WHERE status = 'ACTIVE' |
| `idx_sessions_expires` | (expires_at) | BTREE | WHERE status = 'ACTIVE' |
| `idx_sessions_bot_status` | (bot_id, status) | BTREE | - |
| `idx_sessions_completed_at` | (completed_at) | BTREE | WHERE completed_at IS NOT NULL |
| (auto) | (channel_user_id) | BTREE | - |
| (auto) | (bot_id) | BTREE | - |
| (auto) | (flow_id) | BTREE | - |
| (auto) | (status) | BTREE | - |

**Relationships:**
- `bot` → Bot model (back_populates="sessions")
- `flow` → Flow model (back_populates="sessions")

**Code Reference:** session.py:56-121

## Security Features

**1. PII Encryption:**
- `context` encrypted at rest (contains user inputs)
- `flow_snapshot` encrypted at rest (may contain sensitive config)
- Encryption: AES-256-GCM via `app.utils.encryption`

**2. PII Masking in Logs:**
- `channel_user_id` NOT encrypted (needed for queries/indexes)
- Instead: masked in logs via `logger.mask_pii(channel_user_id, "user_id")`
- Audit logs use masked IDs

**3. Row-Level Locking:**
- `SELECT FOR UPDATE NOWAIT` prevents concurrent modification
- Raises `SessionLockError` if locked (instead of waiting)
- Prevents request queue buildup

**4. Immutability:**
- `flow_snapshot` cannot be modified after creation (enforced by model)
- Ensures version isolation - no mid-session flow changes

**5. Audit Logging:**
Events logged to `audit_logs` table:
- `session_created`
- `session_completed`
- `session_expired`
- `session_error`
- `session_terminated_on_new_flow`

**Code References:**
- Encryption: session.py:130-165, app/utils/encryption.py
- PII masking: session_manager.py:84 (logger.mask_pii)
- Locking: session_manager.py:243 (with_for_update)
- Immutability: session.py:167-178
- Audit logs: session_manager.py (all lifecycle methods)

## Constraints

| Constraint | Value | Enforced By | Exception |
|------------|-------|-------------|-----------|
| Session timeout | 30 minutes (absolute) | SessionManager, background cleanup | `SessionExpiredError` |
| Max context size | 100 KB (UTF-8 encoded JSON) | SessionManager.update_context() | `ContextSizeExceededError` |
| Max array length | 24 items | SessionManager._truncate_arrays() | None (silent truncation) |
| Max auto-progression | 10 consecutive nodes | SessionManager.increment_auto_progression() | `MaxAutoProgressionError` |
| Active session uniqueness | 1 per (channel, user, bot) | Database unique index | `ConstraintViolationError` |
| Flow snapshot immutability | Cannot modify after creation | Session.__setattr__() | `ValueError` |
| Status values | ACTIVE, COMPLETED, EXPIRED, ERROR | Database CHECK constraint | Database error |

**Constants Location:** `app/utils/constants/constraints.py` (SystemConstraints)

**Code References:**
- Timeout: session_manager.py:132, 560-607
- Context size: session_manager.py:294-304, 643-653
- Array length: session_manager.py:533-558
- Auto-progression: session_manager.py:340-378
- Uniqueness: session.py:96-103
- Immutability: session.py:167-178
- Status CHECK: session.py:92-95
