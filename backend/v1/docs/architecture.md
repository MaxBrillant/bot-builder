# Architecture

Bot Builder system design: domain model, request lifecycle, and component interactions.

## Overview

Bot Builder is a multi-tenant conversational bot framework. Users create bots, build conversation flows as directed graphs of nodes, and deploy them via webhooks. When end-users message a bot, the system matches trigger keywords to flows, creates sessions, and executes nodes until the conversation terminates or requires input.

## Domain Model

Core entities and relationships.

| Entity | Primary Key | Purpose | Relationships |
|--------|-------------|---------|---------------|
| User | user_id (UUID) | Account owner | Owns multiple Bots |
| Bot | bot_id (UUID) | Bot definition with webhook authentication | Belongs to User, has multiple Flows and Integrations |
| BotIntegration | integration_id (UUID) | Platform-specific config (WhatsApp, Telegram, Slack) | Belongs to Bot, one per platform |
| Flow | id (UUID) | Conversation flow graph (nodes + routes) | Belongs to Bot, has trigger_keywords |
| Session | session_id (UUID) | Active conversation state | References Bot + Flow, stores snapshot |

**Key Identity Patterns:**

- User: email (unique, case-insensitive), supports OAuth (oauth_provider nullable, currently only `'GOOGLE'` allowed by DB constraint, oauth_id nullable)
- Bot: name (unique per user), has webhook_secret for authentication, description (String(512), nullable), has platform integrations
- BotIntegration: platform (WHATSAPP/TELEGRAM/SLACK), unique per bot+platform, config encrypted at rest (contains API tokens), status (CONNECTED/DISCONNECTED/CONNECTING/ERROR)
- Flow: name (unique per bot), trigger_keywords (array) for activation
- Session: composite unique constraint on (channel, channel_user_id, bot_id) for active sessions only, session_key property returns "channel:channel_user_id:bot_id"

**Session Lifecycle:**

- Status: ACTIVE, COMPLETED, EXPIRED, ERROR
- Timeout: 30 minutes absolute (created_at + 30min = expires_at)
- Uniqueness: Only one active session per user+channel+bot combination
- Immutability: flow_snapshot cannot be modified after creation

**Encrypted Fields:**

Session.context and Session.flow_snapshot are encrypted at rest (LargeBinary storage with hybrid_property accessors).
Session.channel_user_id is plaintext (needed for queries/indexes).

## Request Lifecycle

End-to-end message processing flow.

### 1. Webhook Entry Point

```
POST /webhook/{bot_id}
Headers: X-Webhook-Secret
Body: { channel, channel_user_id, message_text }
```

**Handler:** `app/api/webhooks/core.py`

**Steps:**

1. Validate webhook secret against bot.webhook_secret
2. Verify bot exists and is active
3. Rate limit check (Redis-based per channel_user_id)
4. Sanitize message_text (pattern validation)
5. Stream response via Server-Sent Events (SSE)

**SSE Format:**

```
data: {"message": "Welcome!", "index": 0}

data: {"message": "What is your name?", "index": 1}

data: {"done": true, "session_id": "...", "session_active": true}
```

**Message Callback Protocol:**

The engine uses a `message_callback(message, is_final)` function to stream messages via SSE:
- Non-empty message + `is_final=False`: intermediate message (more coming)
- Non-empty message + `is_final=True`: final message (session ending)
- Empty string `""` + `is_final=True`: signal that engine is done (waiting for input or session ended)

### 2. Conversation Orchestration

**Component:** `app/core/engine.py` - ConversationOrchestrator

**Responsibilities:**

- Get or create session (with row-level lock)
- Match trigger keywords if no active session
- Check session timeout
- Coordinate flow execution
- Handle global errors (SessionLockError, SessionExpiredError, MaxAutoProgressionError)

**Session Lookup:**

```python
session = await session_manager.get_active_session(
    channel, channel_user_id, bot_id,
    for_update=True  # SELECT FOR UPDATE lock
)
```

If no session exists:
- Match message against flow trigger_keywords (bot-scoped, case-insensitive)
- Fallback to wildcard "*" if no specific match
- If no match at all: return "Unknown command" with `session_ended=False` (no session created)
- If match found: create new session with flow snapshot

If session exists:
- Check expires_at vs current time
- Continue flow execution from current_node_id

### 3. Flow Execution

**Component:** `app/core/engine.py` - FlowExecutor

**Auto-progression Loop:**

1. Get current node from session.flow_snapshot
2. Sort routes by priority (specific conditions first, "true" last)
3. Create processor via factory
4. Process node with user context injection (API_ACTION nodes only)
5. Handle result:
   - If needs_input: reset auto_progression to 0, commit, signal "waiting for input" via callback, return
   - If terminal or no routes: complete/error session, return
   - If no next_node but has routes: error (no matching route)
   - Otherwise: move to next_node, clear user_input to `None`, increment auto_progression_count, loop
6. Stop if auto_progression_count > 10 (MaxAutoProgressionError)

**Transaction Boundaries:**

State is only committed to database at two points:
- When a node needs user input (line 555: `db.commit()`)
- When session ends (via `session_manager.complete_session()`, `error_session()`, etc.)

During auto-progression, context and current_node_id changes accumulate in-memory. If the process crashes mid-progression, the session resumes from the last committed state.

**User Input Consumption:**

After each auto-progression step, `user_input` is set to `None` (line 602). This prevents subsequent non-input nodes from receiving the original user's message — only the first node in a chain sees user input.

**Context Injection:**

API_ACTION nodes receive enhanced context with `user.channel` and `user.channel_id`.
Other node types receive plain context. The `user` key is explicitly removed from `result.context` after processing (line 413-414) to prevent it from being persisted to session storage.

**Message History:**

Each message (user/bot/system) appended to session.message_history with timestamp, sender, node_id.
History limited to last 50 entries.

### 4. Node Processing

**Component:** `app/processors/factory.py` + type-specific processors

**Factory Pattern:**

```python
processor = processor_factory.create(node_type)
result = await processor.process(node, context, user_input, session, db)
```

**Processor Registry:**

| Node Type | Processor | File |
|-----------|-----------|------|
| PROMPT | PromptProcessor | app/processors/prompt_processor.py |
| MENU | MenuProcessor | app/processors/menu_processor.py |
| API_ACTION | APIActionProcessor | app/processors/api_action_processor.py |
| LOGIC_EXPRESSION | LogicProcessor | app/processors/logic_processor.py |
| TEXT | TextProcessor | app/processors/text_processor.py |
| SET_VARIABLE | SetVariableProcessor | app/processors/set_variable_processor.py |

**ProcessResult Contract:**

```python
@dataclass
class ProcessResult:
    message: Optional[str]          # Message to send to user
    needs_input: bool               # Wait for user response?
    next_node: Optional[str]        # Next node ID or None
    context: Dict[str, Any]         # Updated session context
    terminal: bool                  # End conversation?
    status: Optional[str]           # COMPLETED, ERROR, etc.
```

**Shared Processor Behavior (BaseProcessor):**

- Route evaluation: evaluate_routes(routes, context) -> first matching target_node
- Interrupt checking: check_interrupt(user_input, interrupts) -> target_node or None
- Terminal detection: check_terminal(node, context) -> ProcessResult or None
- No matching route: raise_no_matching_route(node) -> NoMatchingRouteError

### 5. Route Evaluation

**Component:** `app/core/conditions.py` - ConditionEvaluator

**Priority Sorting:**

Routes sorted before evaluation:
1. Specific conditions (e.g., `age > 18`)
2. Catch-all "true" (always matches)

**Evaluation:**

First matching condition wins. Returns target_node or None.

### 6. Template Rendering

**Component:** `app/core/template_engine.py`

**Syntax:** `{{variable_name}}`

**Context by Node Type:**

- API_ACTION: access to `{{user.channel}}`, `{{user.channel_id}}`, and all context variables
- All other nodes: only context variables (no user prefix)

### 7. Validation

**Component:** `app/core/input_validator.py`

Used by PROMPT and MENU nodes for input validation rules.

### 8. Session Management

**Component:** `app/core/session_manager.py`

**Operations:**

- create_session: Create with flow_snapshot from flow_definition
- get_active_session: Query with optional SELECT FOR UPDATE lock
- complete_session: Mark status=COMPLETED, set completed_at
- expire_session: Mark status=EXPIRED, set completed_at
- error_session: Mark status=ERROR, set completed_at
- check_timeout: Compare expires_at vs current time

## Key Components

### KeywordMatcher

**File:** `app/core/engine.py` (lines 106-178)

**Purpose:** Match user messages to flow trigger keywords within a bot.

**Algorithm:**

1. Normalize input (trim, uppercase)
2. Query flows by bot_id + normalized keyword
3. If no match, try wildcard "*" flow
4. Return Flow or None

**Constraints:**

- Bot-scoped (only searches within specified bot)
- Case-insensitive
- Exact match after normalization (no punctuation, no partial matches)

### FlowExecutor

**File:** `app/core/engine.py` (lines 181-603)

**Purpose:** Execute flow nodes with auto-progression.

**Key Methods:**

- execute_flow: Main loop for node execution
- _process_single_node: Inject user context, invoke processor, clean up
- _handle_terminal: Complete or error session, signal callback
- _inject_user_context: Return enhanced context for API_ACTION nodes
- _update_message_history: Append to session history, truncate to 50

**Error Handling:**

- Node not found: error session, raise NoMatchingRouteError
- Processor error: error session, return generic error message
- Max auto-progression: error session, raise MaxAutoProgressionError

### ConversationOrchestrator

**File:** `app/core/engine.py` (lines 605-802)

**Purpose:** Main entry point for message processing.

**Orchestration:**

1. Get/create session (with lock)
2. Match keywords or continue flow
3. Delegate to FlowExecutor
4. Handle global exceptions (SessionLockError, SessionExpiredError, MaxAutoProgressionError, NoMatchingRouteError)

**HTTP Client Management:**

Lazy initialization of shared httpx.AsyncClient for API_ACTION nodes.

### ProcessorFactory

**File:** `app/processors/factory.py`

**Purpose:** Create node processors with dependency injection.

**Features:**

- Centralized instantiation
- Registration system for custom types
- Singleton cache per factory instance
- API_ACTION gets http_client, others get standard dependencies

**Dependencies Injected:**

- template_engine (TemplateEngine)
- condition_evaluator (ConditionEvaluator)
- validation_system (InputValidator)
- http_client (httpx.AsyncClient, API_ACTION only)
- session_manager (SessionManager)

## Constraints

Hard limits and rules enforced by the system.

| Constraint | Value | Enforcement | Exception Type |
|------------|-------|-------------|----------------|
| Max auto-progression | 10 nodes | FlowExecutor loop check | MaxAutoProgressionError |
| Session timeout | 30 minutes | SessionManager.check_timeout | SessionExpiredError |
| Active sessions per user+bot+channel | 1 | Database unique index | IntegrityError |
| Max message history | 50 entries | FlowExecutor truncation | N/A (automatic) |
| Bot name length | 96 characters | Database column constraint | IntegrityError |
| Flow name length | 96 characters | Database column constraint | IntegrityError |
| Node ID length | 96 characters | Database column constraint | IntegrityError |

**Keyword Matching:**

- Case-insensitive
- Whitespace trimmed
- Exact match only (no partial, no punctuation)
- Bot-scoped (not global)
- Wildcard "*" as fallback

**Route Priority:**

- Specific conditions evaluated first
- "true" catch-all evaluated last
- First match wins

**Template Context:**

- API_ACTION nodes: `{{user.channel}}`, `{{user.channel_id}}`, `{{context_var}}`
- All other nodes: `{{context_var}}` only

**Webhook Authentication:**

- X-Webhook-Secret header required
- Must match bot.webhook_secret
- Validated before any processing

## Related Documentation

- [Node Types](nodes/overview.md) - All node types and their processors
- [Routing](routing/conditions.md) - Condition evaluation and route matching
- [Templates](templates.md) - Variable substitution syntax and context rules
- [Sessions](sessions.md) - Session lifecycle, timeouts, and state management
- [Validation](validation.md) - Input validation rules and error handling
- [Security](security.md) - Webhook authentication, rate limiting, encryption
- [Error Handling](error-handling.md) - Exception types and error responses
