# Bot Builder - System Specifications & Constraints

**Version**: 1.0
**Last Updated**: 2024-12-01

---

## 📋 Table of Contents

0. [System Architecture Overview](#system-architecture-overview)
1. [Flow Structure](#flow-structure)
2. [Core Capabilities](#core-capabilities)
3. [System Constraints](#system-constraints)
4. [Node Type Specifications](#node-type-specifications)
5. [Templating System](#templating-system)
6. [Validation System](#validation-system)
7. [Routing & Logic](#routing--logic)
8. [Session Management](#session-management)
9. [Error Handling & Termination](#error-handling--termination)
10. [Security Considerations](#security-considerations)
11. [What You CAN Do](#what-you-can-do)
12. [What You CANNOT Do](#what-you-cannot-do)
13. [Best Practices](#best-practices)

---

## 0. System Architecture Overview

### Domain Model Hierarchy

The Bot Builder system follows a three-tier hierarchy:

```
User (1) ──→ (N) Bots ──→ (N) Flows
```

**User**: A registered account holder who can create and manage multiple bots.

**Bot**: A logical grouping of conversational flows representing a complete bot application (e.g., "Ride Sharing Bot", "Restaurant Ordering Bot"). Each bot:

- Has a unique identifier (`bot_id`)
- Owns multiple flows
- Has its own webhook URL for message integration
- Can be in `active` or `inactive` status
- Maintains isolated sessions and trigger keywords

**Flow**: A conversation flow definition containing nodes and routing logic. Flows belong to a single bot and define specific conversation paths.

### Integration Architecture

The system is **platform-agnostic** and separates messaging platform integration from core bot logic:

```
┌─────────────────────────────────────────┐
│  Messaging Platform Integration         │
│  (WhatsApp via Evolution API, etc.)     │
│  - Handles platform-specific protocols  │
│  - Translates to normalized format      │
│  - Routes to user's active bot          │
└──────────────┬──────────────────────────┘
               │
               │ HTTP POST to Bot Webhook
               │
               ▼
┌─────────────────────────────────────────┐
│  Bot Builder Core (Platform-Agnostic)   │
│  - Receives: bot_id + channel_user_id + message │
│  - Processes flows                       │
│  - Returns response                      │
└─────────────────────────────────────────┘
```

**Key Design Principles**:

- Core system does NOT know about phone numbers, WhatsApp, or any specific platform
- Each bot gets a unique webhook URL: `https://botbuilder.com/webhook/{bot_id}`
- Integration layers translate platform-specific formats to normalized messages
- Sessions are keyed by: `channel:channel_user_id:bot_id`

**Message Routing Model**:

- **Multi-Bot Support**: Users can interact with multiple bots simultaneously
- **Integration Layer Responsibility**: The integration layer (e.g., Evolution API) determines which bot receives each message based on its own routing logic (outside Bot Builder's scope)
- **Webhook-Based Routing**: The integration layer sends messages directly to specific bot webhooks: `POST /webhook/{bot_id}`
- **Trigger Keywords**: Trigger keywords are scoped per bot - each bot's flows have their own independent trigger keywords
- **Session Isolation**: Each bot maintains its own independent sessions - a user can have active sessions in multiple bots at the same time
- **No Cross-Bot Communication**: Bots cannot access or influence each other's sessions, flows, or data

### Bot Entity

```python
Bot:
  id: UUID (primary key)
  owner_user_id: UUID (foreign key)
  name: string (max 96 characters, e.g., "Tujane Ride Sharing")
  description: string (optional, max 512 characters)
  webhook_url: string (auto-generated: /webhook/{bot_id})
  webhook_secret: string (security token)
  status: enum (active, inactive)
  created_at: timestamp
  updated_at: timestamp
```

**Bot Lifecycle**:

- **Active**: Receives and processes messages via webhook
- **Inactive**: Webhook returns "Bot unavailable" message

### Conceptual Data Model

The following diagram shows the core entities and their relationships:

```
┌─────────────────────────────────────────────────────────────┐
│                         User (Owner)                         │
│  - id: UUID (primary key)                                    │
│  - email: string                                             │
│  - Created bots: N bots                                      │
└────────────────────────┬────────────────────────────────────┘
                         │ owns (1:N)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                            Bot                               │
│  - id: UUID (primary key, globally unique)                   │
│  - owner_user_id: UUID (foreign key → User)                  │
│  - name: string                                              │
│  - webhook_url: string                                       │
│  - status: enum (active, inactive)                           │
│  - Created flows: N flows                                    │
└────────────────────────┬────────────────────────────────────┘
                         │ contains (1:N)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                           Flow                               │
│  - id: UUID (primary key, system-generated, globally unique) │
│  - bot_id: UUID (foreign key → Bot)                          │
│  - name: string (user-provided, unique per bot)              │
│  - trigger_keywords: string[] (unique per bot)               │
│  - nodes: JSON (flow definition)                             │
│  - is_mutable: true (content can be updated)                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                          Session                             │
│  - key: string (composite: "channel:channel_user_id:bot_id") │
│  - bot_id: UUID (references Bot)                             │
│  - flow_snapshot: JSON (immutable copy of flow at start)     │
│  - context: JSON (runtime variables)                         │
│  - status: enum (active, completed, expired, error)          │
│  - created_at: timestamp                                     │
│  - expires_at: timestamp (30 min from creation)              │
└─────────────────────────────────────────────────────────────┘
```

**Key Relationships**:

- **User → Bot**: One-to-Many (a user can own multiple bots)
- **Bot → Flow**: One-to-Many (a bot contains multiple flows)
- **Flow → Session**: One-to-Many (a flow can have multiple active sessions)
- **Bot → Session**: One-to-Many (a bot can have multiple active sessions)

**Uniqueness Constraints**:

- `user.id`: Globally unique (system-assigned UUID)
- `bot.id`: Globally unique (system-assigned UUID)
- `flow.id`: Globally unique (system-assigned UUID)
- `flow.name`: Unique per bot (user-provided, bot-scoped)
- `flow.trigger_keywords[]`: Each keyword unique per bot (user-provided, bot-scoped)
- `session.key`: Unique per channel-user-bot combination

**Immutability vs Mutability**:

- **Immutable IDs**: `user.id`, `bot.id`, `flow.id` (never change once created)
- **Mutable Content**: Flow definitions can be updated (same UUID, new content)
- **Session Snapshots**: Sessions store immutable flow snapshot from session start

### Message Flow Example

```
1. User sends "START" via WhatsApp

2. Evolution API receives message:
   - Looks up user's active bot (stored mapping: +254712345678 → bot_abc123)
   - Routes to active bot's webhook:

   POST https://botbuilder.com/webhook/bot_abc123
   {
     "channel": "whatsapp",
     "channel_user_id": "+254712345678",
     "message_text": "START"
   }

3. Bot Builder:
   - Identifies bot from URL: bot_abc123
   - Creates/resumes session: "whatsapp:+254712345678:bot_abc123"
   - Checks trigger keyword "START" in bot's flows
   - Processes flow nodes
   - Returns response

4. Evolution API sends response back via WhatsApp
```

**Note**: The trigger keyword "START" works because the integration layer routed this message to Bot ABC123's webhook. If the message were sent to a different bot's webhook, that bot would process it instead.

---

## 1. Flow Structure

### JSON Schema Overview

A flow is defined as a JSON object with the following top-level structure:

```json
{
  "name": "string (required)",
  "trigger_keywords": ["array of strings (required)"],
  "variables": { "object (optional)" },
  "defaults": { "object (optional)" },
  "start_node_id": "string (required)",
  "nodes": { "object (required)" }
}
```

### Top-Level Fields

#### `name` (required)

- **Type**: `string`
- **Description**: Human-readable name for the flow (user-provided)
- **System Behavior**:
  - The system automatically generates a **UUID** as the flow's primary key (immutable database identifier)
  - The `name` field is what users provide and see in the API
  - Users reference flows by this `name` in API calls
- **Constraints**:
  - Must be **unique per bot** (not globally unique)
  - Any printable characters allowed (including apostrophes, punctuation, emojis, etc.)
  - Cannot be empty
  - Maximum 96 characters
  - Recommended: Use descriptive names like "Driver Onboarding Flow", "Max's Flow", or "Checkout Process v2"
- **Example**: `"driver_onboarding"`, `"checkout_flow"`, `"customer_support_v1"`, `"Max's Personal Flow"`
- **Uniqueness Scope**: Each bot can have flows with unique names. Different bots can use the same flow names.

#### `trigger_keywords` (required)

- **Type**: `array of strings`
- **Description**: Keywords that activate this flow. **At least one trigger keyword is required.**
- **Uniqueness Constraint**: Each keyword must be **unique per bot** (not globally unique)
  - ✅ Bot A can have Flow 1 with keyword "START"
  - ❌ Bot A cannot have Flow 2 also with keyword "START" (duplicate within same bot)
  - ✅ Bot B can have Flow 1 with keyword "START" (different bot, allowed)
  - ⚠️ **Wildcard `"*"` can only be used by ONE flow per bot** (enforced during validation)
- **Validation on Flow Submission**:
  - **System enforces that at least one trigger keyword must be provided**
  - Returns validation error if `trigger_keywords` array is empty
  - System checks for duplicate keywords within the **same bot's flows**
  - Returns validation error if keyword is already used by another flow in the same bot
  - **System checks that only one flow per bot uses the wildcard `"*"`**
  - Returns validation error if multiple flows in the same bot attempt to use `"*"`
  - Allows the same keyword across different bots (bot-level isolation)
- **Matching Behavior**:
  - **Standalone messages only**: The entire user message must exactly match ONE keyword (after trimming)
  - **Case-insensitive**: "START", "start", "Start" all match
  - **Whitespace trimmed**: " START " matches "START"
  - **No punctuation**: Trigger keywords should NOT contain punctuation (keep them simple)
  - **Allowed characters**: Letters (A-Z, a-z), numbers (0-9), spaces, underscores (_), hyphens (-)
  - **NOT allowed**: Punctuation (!?.), special characters (@#$%^&*), emojis
  - **No partial matches**: "I want to START" does NOT match "START"
  - **No word-in-sentence**: "STARTING" does NOT match "START"
  - **Wildcard fallback**: The `"*"` keyword matches ANY message that doesn't match other specific keywords
- **No regex support**
- **Default**: `[]` (for backward compatibility reference only - will be rejected by validation)
- **Required**: At least one keyword must be provided
- **Example**: `["START", "BEGIN", "HELLO"]` or `["*"]` (wildcard)
- **Matching Examples**:
  - ✅ "START" → Match
  - ✅ "start" → Match
  - ✅ " START " → Match
  - ❌ "START!" → No match (punctuation not allowed)
  - ❌ "I want to START" → No match (not standalone)
  - ❌ "STARTING" → No match (different word)
  - ❌ "START NOW" → No match (multiple words)

##### Wildcard Trigger

The wildcard trigger `"*"` is a special keyword that provides fallback behavior for handling any message that doesn't match specific trigger keywords.

**Purpose**: Catch-all fallback for unmatched messages

**Symbol**: `"*"`

**Priority**: Always checked AFTER specific keywords (fallback only)

- The system first attempts to match the user's message against all specific trigger keywords in the bot's flows
- If no specific keyword matches, the system then checks if any flow has the wildcard `"*"` trigger
- If a wildcard flow exists, it is activated; otherwise, the user receives a "no matching flow" error

**Uniqueness**: Only one flow per bot can use `"*"`

- The wildcard is treated as a special keyword with bot-level uniqueness
- During flow validation, the system checks if another flow in the same bot already uses `"*"`
- If duplicate wildcard found, validation fails with error

**Use Cases**:

- **Fallback handlers**: Handle any unrecognized input with helpful guidance
- **AI-powered bots**: Route all unmatched messages to an AI processing flow
- **Catch-all menus**: Present a main menu when users send unexpected messages
- **Development/testing**: Capture all messages for debugging and analysis

**Examples**:

Bot has three flows:

- Flow A: `["START", "HELP"]`
- Flow B: `["BOOKING"]`
- Flow C: `["*"]` (wildcard)

Message matching behavior:

```
User sends "START"     → Flow A activates (specific match)
User sends "HELP"      → Flow A activates (specific match)
User sends "help"      → Flow A activates (case-insensitive match)
User sends "BOOKING"   → Flow B activates (specific match)
User sends "ANYTHING"  → Flow C activates (wildcard fallback)
User sends "UNKNOWN"   → Flow C activates (wildcard fallback)
User sends "123"       → Flow C activates (wildcard fallback)
User sends "Hello!"    → Flow C activates (wildcard fallback)
```

**Validation Rules**:

- ✅ Wildcard must be the only keyword: `["*"]`
- ❌ Wildcard CANNOT be combined with other keywords: `["*", "START"]` is INVALID
- ❌ Only ONE flow per bot can contain `"*"`
- ❌ Multiple flows cannot share the wildcard
- **Reason**: Since `"*"` accepts everything, adding other keywords is redundant and confusing

**Validation Error Example**:

```json
{
  "status": "error",
  "errors": [
    {
      "type": "duplicate_wildcard_trigger",
      "message": "Wildcard trigger '*' is already used in flow 'fallback_handler' of this bot. Only one flow per bot can use the wildcard trigger.",
      "conflicting_flow_name": "fallback_handler",
      "keyword": "*"
    }
  ]
}
```

**Best Practices**:

- Use wildcard flows to provide helpful guidance when users send unexpected input
- Consider including a menu or help text in wildcard flows to guide users back to valid commands
- Wildcard flows are ideal for AI integration where you want to process natural language
- Test your specific keywords thoroughly before relying on wildcard fallback

**Error Response for Missing Keywords**:

```json
{
  "status": "error",
  "errors": [
    {
      "type": "required_field",
      "message": "At least one trigger keyword is required",
      "field": "trigger_keywords"
    }
  ]
}
```

**Error Response for Duplicate Keyword**:

```json
{
  "status": "error",
  "errors": [
    {
      "type": "duplicate_trigger_keyword",
      "message": "Trigger keyword 'START' is already used in flow 'booking_flow' of this bot",
      "conflicting_flow_name": "booking_flow",
      "keyword": "START"
    }
  ]
}
```

### Flow Lifecycle & Management

#### Multi-Tenant Architecture

**User Isolation**:

- System supports multiple users, each managing their own bots
- User authentication required (implementation-agnostic)
- Each user can create, update, and delete only their own bots and flows
- `flow.name` must be **unique per bot** (not globally unique)
- `flow.id` (UUID) is **globally unique** (system-generated)
- `bot_id` must be **globally unique** across all users

**Bot & Flow Ownership**:

- Every bot belongs to a specific user
- Every flow belongs to a specific bot
- Users cannot access or modify other users' bots or flows
- Sessions are scoped to the bot context

#### Flow Submission

**API-Based Flow Management**:

Flows are submitted to the Bot Builder system via authenticated API:

```
API: Create Flow
Authentication: Required (user credentials)
Content-Type: JSON

{
  "name": "checkout_flow",  // Must be unique within this bot
  "trigger_keywords": ["START"],  // At least one keyword required
  "variables": {...},
  "start_node_id": "node_start",
  "nodes": {...}
}
```

**Validation on Submission**:

- User authentication verified
- Bot ownership verified (user must own the bot)
- Flow validated immediately upon submission
- System generates UUID for flow.id (immutable primary key)
- `flow.name` uniqueness checked within the bot
- If valid: Stored in database with generated UUID, returns success
- If invalid: Returns validation errors, flow not stored

**Response Examples**:

```json
// Success
{
  "status": "success",
  "flow_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",  // System-generated UUID
  "flow_name": "checkout_flow",  // User-provided name
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Flow validated and stored successfully"
}

// Validation Error - Invalid Structure
{
  "status": "error",
  "errors": [
    "Node 'node_missing' referenced in routes but not defined",
    "start_node_id 'node_start' does not exist in nodes"
  ]
}

// Validation Error - Duplicate flow name
{
  "status": "error",
  "errors": [
    "Flow name 'checkout_flow' already exists in this bot"
  ]
}
```

#### Flow Storage

**Database Storage**:

- Flows stored in database
- Persists across server restarts
- Accessible to all Bot Builder instances (shared state)

**Flow Retrieval**:

- Loaded from database when needed
- Redis caching for performance
- Cache invalidated on flow updates

#### Flow Updates

**Update Behavior**:

```
API: Update Flow
Authentication: Required (user credentials)
Flow Identifier: flow_id (UUID) or flow_name
Content-Type: JSON

{
  "name": "checkout_flow",  // Can be same or different
  ...updated flow definition...
}
```

**Update Rules**:

- User must own the bot/flow to update it (enforced by authentication)
- Flow is identified by its UUID (immutable)
- Flow content is mutable - updates overwrite previous version
- Flow name can be changed during update (must remain unique within bot)
- Active sessions continue using flow snapshot they started with
- New sessions use updated version
- Validation applied to updated flow before accepting
  **Note**: Trigger keywords must be unique within each bot. When deploying a new version with the same keyword, remove the keyword from the old flow first. Flow names must be unique within each bot (not globally).

#### Validation Checks

**Validation Algorithm**:

The system uses a **two-pass validation** approach to handle forward references:

1. **Pass 1 - Indexing**: Build index of all node IDs in the flow
2. **Pass 2 - Validation**: Validate all references and constraints

This allows nodes to reference other nodes that appear later in the JSON (order-independent).

**Performed on Submission**:

- User authentication valid
- User has permission to create/update flows in this bot
- JSON syntax valid
- All required fields present (name, trigger_keywords, start_node_id, nodes)
- **At least one trigger_keywords provided** - empty array not allowed
- **flow.name unique per bot** - no duplicate names within the same bot's flows
- **trigger_keywords unique per bot** - no duplicate keywords within the same bot's flows
- **Wildcard trigger unique per bot** - only one flow per bot can use the `"*"` wildcard trigger
- Node IDs unique within flow
- start_node_id references existing node
- All route target_nodes reference existing nodes
- **Only start node has no parent** - only the start_node_id should have no parent (not be referenced in any route). All other nodes must have at least one parent (be referenced as target_node in at least one route). Orphan nodes are invalid.
- **Route conditions unique per node** - no duplicate conditions within a single node's routes array (case-insensitive)
- **Circular references allowed only if cycle includes input node** - Cycles containing at least one PROMPT or MENU node are allowed (user input breaks potential infinite loops). Cycles with only non-input nodes (TEXT, API_ACTION, LOGIC_EXPRESSION) are rejected.
- Variable types valid (STRING, NUMBER, BOOLEAN, ARRAY)
- fail_route is required when retry_logic is defined, and must reference existing node
- Constraints respected:
  - Max 48 nodes per flow
  - Max 8 routes per node
  - ID lengths ≤ 96 characters
  - Node types valid (PROMPT, MENU, API_ACTION, etc.)

**Validation Response**:

```json
{
  "status": "error",
  "flow_name": "checkout_flow",
  "errors": [
    {
      "type": "duplicate_flow_name",
      "message": "Flow name 'checkout_flow' already exists in this bot",
      "suggestion": "Use a different name or update the existing flow"
    },
    {
      "type": "missing_node",
      "message": "Route target 'node_missing' not found in nodes",
      "location": "nodes.node_start.routes[0].target_node"
    },
    {
      "type": "circular_reference",
      "message": "Circular reference without input node detected: node_a → node_b → node_a",
      "suggestion": "Add a PROMPT or MENU node to the cycle, or remove the circular routing"
    },
    {
      "type": "orphan_nodes",
      "message": "Orphan nodes detected (nodes with no parent): 'Prompt 2' (node_prompt_2), 'Menu 3' (node_menu_3). Only the start node should have no parent. These nodes are unreachable in the flow.",
      "location": "nodes"
    }
  ]
}
```

#### Active Session Handling

**Flow Version Isolation**:

```
10:00 - Flow submitted and stored (UUID: abc-123, name: "checkout")
10:05 - User A starts session (uses flow snapshot from 10:00)
10:10 - Flow updated with same UUID (content changed)
10:15 - User B starts session (uses updated flow from 10:10)
10:20 - User A continues session (still uses original snapshot from 10:00)
10:25 - User A completes (original snapshot)
10:30 - User B continues (updated version from 10:10)
```

**Session-Flow Binding**:

- Sessions store flow snapshot or version reference
- Flow updates don't affect active sessions
- Ensures consistent user experience
- No mid-session flow changes

#### Multi-Instance Deployment

**Shared Flow State**:

```
Bot Builder Instance 1 ←
                         → Database (flows table) ←
Bot Builder Instance 2 ←                         → Load Balancer
                         → Database (flows table) ←
Bot Builder Instance 3 ←
```

**Synchronization**:

- All instances read flows from shared database
- Redis cache with TTL or invalidation
- Flow updates visible to all instances
- No file-based synchronization needed

#### `variables` (optional)

- **Type**: `object`
- **Description**: Flow-wide variable definitions with types and defaults
- **Structure**:
  ```json
  {
    "variable_name": {
      "type": "STRING|NUMBER|BOOLEAN|ARRAY",
      "default": null | value
    }
  }
  ```
- **Supported Types**:
  - `STRING`: Text values (default max 256 characters)
  - `NUMBER`: Numeric values (integers and decimals, standard JSON number)
  - `BOOLEAN`: true/false
  - `ARRAY`: Lists of items (default max 24 items)

  **Important**: Type names are UPPERCASE as they are defined as enum values in the backend.
- **Type Enforcement & Conversion Process**:
  1. User provides input (always received as string)
  2. PROMPT validates the input format (regex or expression validation)
  3. If validation passes, system attempts type conversion based on declared variable type
  4. If conversion succeeds, value is saved to context
  5. If conversion fails, user sees error and must retry (counts toward max attempts)
  6. **Note**: Validation ensures input is in convertible format (e.g., `input.isNumeric()` ensures string can convert to number)
  7. **Output Mappings**: This type enforcement also applies to [`output_mapping`](#menu-node-config) (MENU nodes) and [`response_map`](#api_action-node-config) (API_ACTION nodes). During conversation, when mapping extracted values to variables, the system attempts conversion to the variable's declared type. Conversion failures in mappings result in `null` (don't count toward max validation attempts). See [Type Inference in Output Mappings](#type-inference-in-output-mappings) for details.
- **Default Value Constraints**:
  - String defaults: Maximum 256 characters
  - Array defaults: Maximum 24 items
  - Number defaults: Standard JSON number format
  - Boolean defaults: true or false only
  - **Runtime**: All arrays written to context (from any source) are enforced to 24 items max and truncated if exceeded
- **Example**:
  ```json
  "variables": {
    "user_name": { "type": "STRING", "default": null },
    "age": { "type": "NUMBER", "default": 0 },
    "is_verified": { "type": "BOOLEAN", "default": false },
    "items": { "type": "ARRAY", "default": [] }
  }
  ```

#### `defaults` (optional)

- **Type**: `object`
- **Description**: Flow-wide default configurations
- **Structure**:
  ```json
  {
    "retry_logic": {
      "max_attempts": 3,
      "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})",
      "fail_route": "node_id"  // REQUIRED when retry_logic is defined
    }
  }
  ```
- **Note**: If `retry_logic` is defined, `fail_route` must be specified. `max_attempts` and `counter_text` have defaults.
- **Fields**:
  - `max_attempts`: Maximum validation retry attempts (default: 3, valid range: 1-10)
  - `counter_text`: Template for retry counter display (default: "(Attempt {{current_attempt}} of {{max_attempts}})", max 512 characters)
  - `fail_route`: Node to redirect to after max attempts exceeded (**REQUIRED** - must always be specified when retry_logic is defined; must reference existing node ID in the flow, typically TEXT or END node; validated during two-pass validation)

#### `start_node_id` (required)

- **Type**: `string`
- **Description**: ID of the first node to execute
- **Constraints**:
  - Must reference an existing node ID
  - Cannot be empty
- **Example**: `"node_check_driver_status"`

#### `nodes` (required)

- **Type**: `object`
- **Description**: Dictionary of all nodes in the flow
- **Structure**: `{ "node_id": { node_definition } }`
- **Constraints**:
  - Must contain at least one node
  - Node IDs must be unique
  - Must include the `start_node_id` node

### Node Structure

Every node has this base structure:

```json
{
  "id": "string (required)",
  "name": "string (required)",
  "type": "PROMPT|MENU|API_ACTION|LOGIC_EXPRESSION|TEXT|END (required)",
  "config": { "object (required)" },
  "routes": [ "array (optional)" ],
  "position": { "object (required)" }
}
```

#### Node Base Fields

##### `id` (required)

- **Type**: `string`
- **Description**: Unique identifier for this node
- **Constraints**:
  - Must match the key in nodes object
  - Alphanumeric and underscores only
  - No spaces
- **Example**: `"node_get_origin"`

##### `name` (required)

- **Type**: `string`
- **Description**: Human-readable display name for the node
- **Constraints**:
  - Maximum 50 characters
  - Cannot be empty or whitespace only
  - Should be unique within the flow (case-insensitive)
- **Example**: `"Get User Location"`

##### `type` (required)

- **Type**: `string enum`
- **Description**: Node type determining behavior
- **Values**: `PROMPT`, `MENU`, `API_ACTION`, `LOGIC_EXPRESSION`, `TEXT`, `END`
- **Example**: `"PROMPT"`

##### `config` (required)

- **Type**: `object`
- **Description**: Node-specific configuration
- **Structure**: Varies by node type (see Node Type Specifications section)

##### `routes` (required for all nodes except END)

- **Type**: `array of route objects`
- **Description**: Defines possible next nodes based on conditions
- **Structure**:
  ```json
  [
    {
      "condition": "string (required, max 512 characters)",
      "target_node": "string (required)"
    }
  ]
  ```
- **Constraints**:
  - Routes evaluated in order (first match wins)
  - `target_node` must reference existing node ID
  - END nodes cannot have routes
  - **Route condition length**: Maximum 512 characters (same as expression limit)
  - **Route conditions must be unique** - Each node can only have one route with a given condition (case-insensitive comparison: 'true' === 'TRUE')
  - **Example**:
  ```json
  "routes": [
    { "condition": "success", "target_node": "node_next" },
    { "condition": "error", "target_node": "node_error" }
  ]
  ```

##### `position` (required)

- **Type**: `object`
- **Description**: Node position on the visual canvas for the flow editor
- **Structure**:
  ```json
  {
    "x": number,
    "y": number
  }
  ```
- **Constraints**:
  - Must have both `x` and `y` properties
  - Both values must be numeric (integer or float)
  - Negative values allowed (canvas extends in all directions)
  - No min/max bounds (infinite canvas)
- **Example**: `{"x": 250.5, "y": 100}` or `{"x": -150, "y": -200}`

### Node Configuration by Type

#### PROMPT Node Config

```json
{
  "type": "PROMPT",
  "text": "string (required)",
  "save_to_variable": "string (required)",
  "validation": {
    "type": "REGEX|EXPRESSION (required)",
    "rule": "string (required)",
    "error_message": "string (required)"
  },
  "interrupts": [
    {
      "input": "string (required)",
      "target_node": "string (required)"
    }
  ]
}
```

**Required**: `type`, `text`, `save_to_variable`
**Optional**: `validation`, `interrupts`

**Note**: The `type` field in the config must match the node's `type` field. The backend automatically injects this during validation if omitted, but it's recommended to include it explicitly.

#### MENU Node Config

```json
{
  "type": "MENU",
  "text": "string (required)",
  "source_type": "STATIC|DYNAMIC (required)",
  "source_variable": "string (required if DYNAMIC)",
  "item_template": "string (required if DYNAMIC)",
  "static_options": [
    {
      "label": "string (required)"
    }
  ],
  "interrupts": [
    {
      "input": "string (required)",
      "target_node": "string (required)"
    }
  ],
  "error_message": "string (optional)",
  "output_mapping": [
    {
      "source_path": "string (required, max 256 chars, dot notation only)",
      "target_variable": "string (required)"
    }
  ]
}
```

**Required**: `type`, `text`, `source_type`
**Conditionally Required**:

- `source_variable` and `item_template` if `source_type` is `DYNAMIC`
- `static_options` if `source_type` is `STATIC`

**Optional**: `interrupts`, `error_message`, `output_mapping`

**Note**: `output_mapping` only works with DYNAMIC source_type.

**output_mapping Field Handling**:

When extracting fields from selected menu item, the system uses **type inference** based on the flow's `variables` section:

1. **Extract value** using `source_path` from the selected item (dot notation only, max 256 characters)
   - ✅ Supported: `id`, `data.user.name`, `items.0.price` (array index with dot)
   - ❌ NOT supported: `items[0].price` (bracket notation)
2. **Look up** `target_variable` in the flow's `variables` section to determine the declared type
3. **Attempt type conversion** based on the variable's declared type (STRING, NUMBER, BOOLEAN, ARRAY)
4. **On success**: Save converted value to context
5. **On failure** (missing path OR conversion error): Set variable to `null`
6. **All mappings execute independently** - one failure doesn't affect others

**Source Path Syntax**:

The `source_path` uses **dot notation** to traverse the selected menu item's structure:

**Dictionary (Object) Access**:
- Direct field: `id`, `name`, `status`
- Nested fields: `user.name`, `driver.profile.rating`
- Deep nesting: `data.nested.deep.field` (unlimited depth)

**Array Access**:
- Array element: `items.0`, `tags.2` (zero-based index with dot)
- Element field: `items.0.id`, `drivers.1.name`
- Nested arrays: `data.trips.0.stops.1.location`

**NOT Supported**:
- Bracket notation: `items[0]` ❌ (use `items.0` instead)
- Array length: `items.length` ❌
- Leading/trailing dots: `.field`, `field.` ❌
- Empty path: `""` ❌

**Type Inference Behavior**:

- No `type` field exists in `output_mapping` structure
- Type is determined by variable declaration in flow's `variables` section
- Missing or null fields in source → variable set to `null`
- Invalid type conversion (e.g., "abc" to number) → variable set to `null`
- `selection` variable automatically set to numeric index as **number** (1, 2, 3, etc.)

**Example**:

```json
// Flow variables declaration:
"variables": {
  "trip_id": { "type": "STRING", "default": null },
  "driver": { "type": "STRING", "default": null },
  "seats_available": { "type": "NUMBER", "default": 0 },
  "is_verified": { "type": "BOOLEAN", "default": false }
}

// Selected item (user chose option 2):
// {"id": "123", "seats_available": "5", "is_verified": true}
// Note: "driver" field is missing

"output_mapping": [
  {"source_path": "id", "target_variable": "trip_id"},
  {"source_path": "driver", "target_variable": "driver"},
  {"source_path": "seats_available", "target_variable": "seats_available"},
  {"source_path": "is_verified", "target_variable": "is_verified"}
]

// Result in context (after type inference):
// selection = 2  (number, automatically set)
// trip_id = "123"  (string, as declared)
// driver = null  (missing field)
// seats_available = 5  (converted from "5" string to number)
// is_verified = true  (boolean, as declared)
```

**Type Conversion Examples**:

```json
// Source data: {"price": "29.99", "quantity": "3", "active": "true"}
// Variable declarations: price (string), quantity (number), active (boolean)

// Result:
// price = "29.99"  (kept as string)
// quantity = 3  (converted to number)
// active = true  (converted to boolean)

// Source data: {"invalid_number": "abc", "missing_field": null}
// Variable declarations: invalid_number (number), missing_field (string)

// Result:
// invalid_number = null  (conversion failed)
// missing_field = null  (null in source)
```

See [Type Inference in Output Mappings](#type-inference-in-output-mappings) section for detailed behavior across node types.

#### API_ACTION Node Config

```json
{
  "type": "API_ACTION",
  "request": {
    "method": "GET|POST|PUT|DELETE|PATCH (required)",
    "url": "string (required, supports templates for query parameters)",
    "headers": [
      {
        "name": "string (required, max 128 chars)",
        "value": "string (required, max 2048 chars, supports templates)"
      }
    ],
    "body": "string (optional, JSON string with template support)"
  },
  "response_map": [
    {
      "source_path": "string (required, max 256 chars, supports dot notation and * for root)",
      "target_variable": "string (required)"
    }
  ],
  "success_check": {
    "status_codes": [200, 201],
    "expression": "string (optional)"
  }
}
```

**Important Notes**:
- **headers**: Array of objects (max 10 headers), each with `name` and `value` properties. Both fields support template variables.
- **body**: JSON string (not object). Template variables are rendered before sending. For POST/PUT/PATCH requests only.

**response_map Behavior**:

The `response_map` uses **type inference** to convert API response values based on the flow's `variables` section:

1. **Extract value** from response using `source_path` (dot notation only, max 256 characters)
   - ✅ Supported: `data.user.id`, `items.0.name` (array index with dot), `*` (root reference)
   - ❌ NOT supported: `items[0].name` (bracket notation)
2. **Look up** `target_variable` in flow's `variables` section to determine declared type
3. **Attempt type conversion** based on variable's declared type (STRING, NUMBER, BOOLEAN, ARRAY)
4. **On success**: Save converted value to context
5. **On failure** (missing path OR conversion error): Set variable to `null`
6. **All mappings execute independently** - conversion failures don't affect other mappings

**Source Path Syntax**:

The `source_path` uses **dot notation** to traverse the API response structure. The syntax adapts based on the **root response type**:

**Dictionary (Object) Root Response**:
- Direct field: `status`, `data`, `user_id`
  - Example response: `{"status": "ok", "data": {...}}`
  - Path: `status` → `"ok"`
- Nested fields: `data.user.name`, `result.profile.email`
  - Example response: `{"data": {"user": {"name": "Alice"}}}`
  - Path: `data.user.name` → `"Alice"`
- Array within dict: `items`, `items.0`, `items.0.id`
  - Example response: `{"items": [{"id": "123"}]}`
  - Path: `items.0.id` → `"123"`

**Array Root Response** (requires `*` prefix):
- Entire array: `*`
  - Example response: `[{"id": "aaa"}, {"id": "bbb"}]`
  - Path: `*` → `[{"id": "aaa"}, {"id": "bbb"}]`
- Array element: `*.0`, `*.1`, `*.5`
  - Example response: `[{"id": "aaa"}, {"id": "bbb"}]`
  - Path: `*.0` → `{"id": "aaa"}`
- Element field: `*.0.id`, `*.1.name`
  - Example response: `[{"id": "aaa", "name": "Alice"}]`
  - Path: `*.0.id` → `"aaa"`
- Nested access: `*.0.profile.email`
  - Example response: `[{"profile": {"email": "a@example.com"}}]`
  - Path: `*.0.profile.email` → `"a@example.com"`

**Primitive Root Response** (requires `*`):
- Entire value: `*`
  - Example response: `"token_abc123"`
  - Path: `*` → `"token_abc123"`
  - Example response: `12345`
  - Path: `*` → `12345`

**Path Syntax Rules**:

- ✅ Root dict field: `field`, `data.nested`
- ✅ Root array: `*`, `*.0`, `*.0.field`
- ✅ Root primitive: `*`
- ✅ Nested arrays in dict: `data.items.0.id`
- ❌ Bracket notation: `items[0]` (use `items.0`)
- ❌ `*` on dict root: `*.field` (use `field` directly)
- ❌ `*` for nested arrays: `data.items.*.0` (use `data.items.0`)
- ❌ Bare index on root array: `0` (use `*.0`)
- ❌ Array length: `items.length`
- ❌ Empty path: `""`

**Why `*` is Required for Root Arrays**:

When the API returns an array at root level, the `*` prefix explicitly signals "I'm working with the root as a collection." This prevents ambiguity:
- `"0"` on its own looks like accessing a field named "0" (which doesn't exist)
- `"*.0"` clearly indicates "access index 0 of the root array"

For dictionary roots, field names are unambiguous, so no prefix is needed.

**Type Inference Details**:

- **No `type` field** exists in `response_map` structure (removed)
- Type is determined by variable declaration in flow's `variables` section
- Missing response paths → variable set to `null`
- Invalid conversions → variable set to `null` (no errors thrown)
- Conversion failures in mappings **do not** count toward validation retry attempts

**Example 1: Dictionary Root Response**

```json
// Flow variables declaration:
"variables": {
  "user_id": { "type": "STRING", "default": null },
  "age": { "type": "NUMBER", "default": 0 },
  "is_verified": { "type": "BOOLEAN", "default": false },
  "tags": { "type": "ARRAY", "default": [] }
}

// API Response:
// {"data": {"user_id": "user_123", "age": "25", "is_verified": "true", "tags": ["active", "premium"]}}

"response_map": [
  {"source_path": "data.user_id", "target_variable": "user_id"},
  {"source_path": "data.age", "target_variable": "age"},
  {"source_path": "data.is_verified", "target_variable": "is_verified"},
  {"source_path": "data.tags", "target_variable": "tags"}
]

// Result in context (after type inference):
// user_id = "user_123"  (string, as declared)
// age = 25  (converted from "25" string to number)
// is_verified = true  (converted from "true" string to boolean)
// tags = ["active", "premium"]  (array, as declared)
```

**Example 2: Array Root Response (Entire Array)**

```json
// Flow variables declaration:
"variables": {
  "all_rides": { "type": "ARRAY", "default": [] }
}

// API Response:
// [{"id": "aaa", "where_from": "Gitega", "price": 10000}, {"id": "bbb", "where_from": "Bujumbura", "price": 15000}]

"response_map": [
  {"source_path": "*", "target_variable": "all_rides"}
]

// Result in context:
// all_rides = [{"id": "aaa", "where_from": "Gitega", "price": 10000}, {"id": "bbb", "where_from": "Bujumbura", "price": 15000}]
// Note: If array exceeds 24 items, it will be truncated to first 24
```

**Example 3: Array Root Response (Extract Fields from First Item)**

```json
// Flow variables declaration:
"variables": {
  "ride_id": { "type": "STRING", "default": null },
  "origin": { "type": "STRING", "default": null },
  "destination": { "type": "STRING", "default": null },
  "price": { "type": "NUMBER", "default": 0 }
}

// API Response:
// [{"id": "aafa1564", "where_from": "Gitega", "where_to": "Bujumbura", "price_per_seat": 10000}]

"response_map": [
  {"source_path": "*.0.id", "target_variable": "ride_id"},
  {"source_path": "*.0.where_from", "target_variable": "origin"},
  {"source_path": "*.0.where_to", "target_variable": "destination"},
  {"source_path": "*.0.price_per_seat", "target_variable": "price"}
]

// Result in context:
// ride_id = "aafa1564"  (string)
// origin = "Gitega"  (string)
// destination = "Bujumbura"  (string)
// price = 10000  (number)
```

**Example 4: Array Root Response (Mixed Extraction)**

```json
// Flow variables declaration:
"variables": {
  "all_users": { "type": "ARRAY", "default": [] },
  "first_user_id": { "type": "STRING", "default": null },
  "first_user_name": { "type": "STRING", "default": null }
}

// API Response:
// [{"id": "aaa", "name": "Alice"}, {"id": "bbb", "name": "Bob"}]

"response_map": [
  {"source_path": "*", "target_variable": "all_users"},
  {"source_path": "*.0.id", "target_variable": "first_user_id"},
  {"source_path": "*.0.name", "target_variable": "first_user_name"}
]

// Result in context:
// all_users = [{"id": "aaa", "name": "Alice"}, {"id": "bbb", "name": "Bob"}]
// first_user_id = "aaa"
// first_user_name = "Alice"
```

**Example 5: Primitive Root Response**

```json
// Flow variables declaration:
"variables": {
  "auth_token": { "type": "STRING", "default": null }
}

// API Response (raw string):
// "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

"response_map": [
  {"source_path": "*", "target_variable": "auth_token"}
]

// Result in context:
// auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Handling Missing/Invalid Data**:

```json
// API Response: {"data": {"user_id": "user_123"}}
// Note: age, is_verified, tags are missing

// Variables declared: user_id (string), age (number), is_verified (boolean), tags (array)

"response_map": [
  {"source_path": "data.user_id", "target_variable": "user_id"},
  {"source_path": "data.age", "target_variable": "age"},
  {"source_path": "data.is_verified", "target_variable": "is_verified"},
  {"source_path": "data.tags", "target_variable": "tags"}
]

// Result:
// user_id = "user_123"  (extracted successfully)
// age = null  (missing in response)
// is_verified = null  (missing in response)
// tags = null  (missing in response)

// Invalid conversion example:
// API Response: {"count": "not_a_number"}
// Variable: count (number)
// Result: count = null  (conversion failed)
```

**Empty Array Response**:

```json
// API Response: []

"response_map": [
  {"source_path": "*", "target_variable": "results"}
]

// Result:
// results = []  (empty array)
```

See [Type Inference in Output Mappings](#type-inference-in-output-mappings) section for comprehensive details.

**Success Check Behavior**:

The `success_check` determines whether an API call succeeded. Both `status_codes` and `expression` are evaluated on **equal footing with AND logic**:

- **No success_check provided**: Default behavior checks if status code is in 200-299 range
- **Only `status_codes` provided**: Status code must be in the specified list
- **Only `expression` provided**: Expression must evaluate to `true`
- **Both provided**: **BOTH conditions must pass** (AND logic)

**Available variables in expression**:

- `response.body.*` - Parsed JSON response fields
- `response.status` - HTTP status code
- `response.headers.*` - Response headers

**Example**:

```json
"success_check": {
  "status_codes": [200, 201],
  "expression": "response.body.id != null && response.body.success == true"
}
```

In this example, the API call is considered successful **only if**:
1. Status code is 200 or 201, **AND**
2. Response body has `id != null` and `success == true`

If status is 200 but `success == false`, the call routes to the `error` condition.

**Required**: `request` with `method` and `url`
**Optional**: `response_map`, `success_check`, `headers`, `body`

### Type Inference in Output Mappings

Both [`MENU`](#menu-node-config) and [`API_ACTION`](#api_action-node-config) nodes support output mappings that extract data and store it in context variables. These mappings use **type inference** to automatically convert extracted values to the appropriate type based on the flow's variable declarations.

#### How Type Inference Works

**Single Source of Truth**: Variable types are defined once in the flow's [`variables`](#variables-optional) section. The system references this declaration when performing type conversions during output mapping.

**Inference Process**:

1. **Value Extraction**: Extract raw value from source (menu item or API response)
2. **Type Lookup**: Look up target variable in flow's `variables` section
3. **Type Conversion**: Attempt to convert extracted value to declared type
4. **Assignment**:
   - On success → save converted value to context
   - On failure → set variable to `null`

**Supported Conversions**:

| Declared Type | Conversion Behavior               | Examples                                                                              |
| ------------- | --------------------------------- | ------------------------------------------------------------------------------------- |
| `STRING`      | No conversion, value stored as-is | `"123"` → `"123"`, `123` → `"123"`                                                    |
| `NUMBER`      | Parse to numeric value            | `"42"` → `42`, `"3.14"` → `3.14`, `"abc"` → `null`                                    |
| `BOOLEAN`     | Parse to true/false               | `"true"` → `true`, `"false"` → `false`, `1` → `true`, `0` → `false`, `"yes"` → `null` |
| `ARRAY`       | Expect array value                | `["a","b"]` → `["a","b"]`, `"abc"` → `null`                                           |

#### Benefits of Type Inference

1. **No Redundancy**: Types defined once in `variables`, not repeated in every mapping
2. **Consistency**: All nodes use the same type definitions from a single source
3. **Maintainability**: Changing a variable's type updates behavior across all mappings
4. **Simplicity**: Mapping definitions only specify source and target, not type
5. **Graceful Failure**: Invalid conversions set `null` instead of crashing the flow

#### Failure Handling

**When Type Conversion Fails**:

- Variable is set to `null` in context
- Flow execution continues normally
- No error message shown to user
- Does not count toward validation retry attempts
- Other mappings in the same node continue to execute

**Common Failure Scenarios**:

```json
// Scenario 1: Missing path
// Source: {"id": "123"}
// Mapping: {"source_path": "name", "target_variable": "user_name"}
// Result: user_name = null

// Scenario 2: Type conversion error
// Source: {"age": "twenty-five"}
// Variable: age (number)
// Mapping: {"source_path": "age", "target_variable": "age"}
// Result: age = null

// Scenario 3: Null in source
// Source: {"count": null}
// Variable: count (number)
// Mapping: {"source_path": "count", "target_variable": "count"}
// Result: count = null
```

#### Complete Example: MENU with Type Inference

```json
{
  "variables": {
    "trip_id": { "type": "STRING", "default": null },
    "departure_time": { "type": "STRING", "default": null },
    "available_seats": { "type": "NUMBER", "default": 0 },
    "price": { "type": "NUMBER", "default": 0 },
    "is_express": { "type": "BOOLEAN", "default": false }
  },
  "nodes": {
    "node_select_trip": {
      "type": "MENU",
      "config": {
        "text": "Select a trip:",
        "source_type": "DYNAMIC",
        "source_variable": "trips",
        "item_template": "{{index}}. {{item.from}} → {{item.to}} at {{item.time}} ({{item.seats}} seats)",
        "output_mapping": [
          { "source_path": "id", "target_variable": "trip_id" },
          {
            "source_path": "departure_time",
            "target_variable": "departure_time"
          },
          {
            "source_path": "available_seats",
            "target_variable": "available_seats"
          },
          { "source_path": "price_ksh", "target_variable": "price" },
          { "source_path": "is_express", "target_variable": "is_express" }
        ]
      },
      "routes": [{ "condition": "true", "target_node": "node_confirm" }]
    }
  }
}

// User selects option 2 from:
// trips = [
//   {"id": "t1", "departure_time": "08:00", "available_seats": "4", "price_ksh": "500", "is_express": "true"},
//   {"id": "t2", "departure_time": "10:00", "available_seats": "2", "price_ksh": "450", "is_express": false}
// ]

// Result in context after type inference:
// selection = 2 (number, automatically set by MENU)
// trip_id = "t2" (string, no conversion needed)
// departure_time = "10:00" (string, no conversion needed)
// available_seats = 2 (converted from "2" string to number)
// price = 450 (converted from "450" string to number)
// is_express = false (boolean, no conversion needed)
```

#### Complete Example: API_ACTION with Type Inference

```json
{
  "variables": {
    "booking_id": { "type": "STRING", "default": null },
    "total_amount": { "type": "NUMBER", "default": 0 },
    "is_confirmed": { "type": "BOOLEAN", "default": false },
    "payment_methods": { "type": "ARRAY", "default": [] }
  },
  "nodes": {
    "node_create_booking": {
      "type": "API_ACTION",
      "config": {
        "request": {
          "method": "POST",
          "url": "https://api.example.com/bookings",
          "body": {
            "trip_id": "{{trip_id}}",
            "user_id": "{{user.channel_id}}"
          }
        },
        "response_map": [
          { "source_path": "data.booking_id", "target_variable": "booking_id" },
          {
            "source_path": "data.total_amount",
            "target_variable": "total_amount"
          },
          {
            "source_path": "data.confirmed",
            "target_variable": "is_confirmed"
          },
          {
            "source_path": "data.payment_methods",
            "target_variable": "payment_methods"
          }
        ],
        "success_check": {
          "status_codes": [200, 201]
        }
      },
      "routes": [
        { "condition": "success", "target_node": "node_payment" },
        { "condition": "error", "target_node": "node_booking_error" }
      ]
    }
  }
}

// API Response:
// {
//   "data": {
//     "booking_id": "BK12345",
//     "total_amount": "1500",
//     "confirmed": "true",
//     "payment_methods": ["mpesa", "card"]
//   }
// }

// Result in context after type inference:
// booking_id = "BK12345" (string, no conversion)
// total_amount = 1500 (converted from "1500" string to number)
// is_confirmed = true (converted from "true" string to boolean)
// payment_methods = ["mpesa", "card"] (array, no conversion)
```

#### Best Practices

1. **Always Declare Variables**: Define all variables with types in the flow's `variables` section before using them in mappings

2. **Choose Appropriate Types**: Use the type that matches your business logic

   - Numeric IDs that need comparison: `number`
   - IDs used as references: `string`
   - Counts, quantities, amounts: `number`
   - Flags, status indicators: `boolean`
   - Lists of items: `array`

3. **Handle Null Values**: After mappings, use LOGIC_EXPRESSION nodes to check for `null` values if the data is critical:

   ```json
   {
     "type": "LOGIC_EXPRESSION",
     "routes": [
       {
         "condition": "context.user_id != null",
         "target_node": "node_continue"
       },
       {
         "condition": "context.user_id == null",
         "target_node": "node_error_missing_data"
       }
     ]
   }
   ```

4. **Validate API Responses**: Check for missing or invalid data before using it:

   ```json
   {
     "type": "LOGIC_EXPRESSION",
     "routes": [
       {
         "condition": "context.count > 0 && context.count != null",
         "target_node": "node_show_results"
       },
       { "condition": "true", "target_node": "node_no_results" }
     ]
   }
   ```

5. **Document Expected Formats**: Comment your API contracts and menu data structures to ensure they provide convertible values

#### Comparison with PROMPT Type Conversion

**PROMPT nodes** also perform type conversion, but with different failure behavior:

- **PROMPT**: Conversion failure → validation error → user must retry (counts toward max attempts)
- **Output Mappings**: Conversion failure → sets `null` → flow continues (no retry)

**Example**:

```json
// PROMPT: User enters "abc" for number variable
// Result: Validation error, user sees error message, must retry

// API_ACTION response_map: API returns {"age": "abc"}
// Result: age = null, flow continues without error
```

This design allows flows to continue gracefully when external data is malformed, while enforcing correctness for user-provided input.

#### LOGIC_EXPRESSION Node Config

```json
{
  "type": "LOGIC_EXPRESSION"
}
```

**Required**: `type`

**Note**: LOGIC_EXPRESSION nodes perform internal conditional routing based on the `routes` array. All logic is defined in the route conditions, not in the node config.

#### Text Node Config

```json
{
  "type": "TEXT",
  "text": "string (required)"
}
```

**Required**: `type`, `text`

#### END Node Config

```json
{
  "type": "END"
}
```

**Required**: `type`

### Flow Structure Rules

#### ✅ Required Elements

1. **Must have**:

   - `name`
   - `start_node_id`
   - `nodes` object with at least one node
   - Start node must exist in nodes

2. **Every node must have**:

   - `id` matching its key
   - `type`
   - `config` appropriate for its type
   - `routes` (except END nodes)

3. **Routes must**:
   - Have valid `condition`
   - Reference existing `target_node`

#### ❌ Common Mistakes

1. **Missing Required Fields**

   ```json
   // ❌ BAD - Missing save_to_variable
   {
     "type": "PROMPT",
     "config": {
       "text": "What's your name?"
     }
   }
   ```

2. **Invalid Node References**

   ```json
   // ❌ BAD - target_node doesn't exist
   {
     "routes": [{ "condition": "true", "target_node": "node_nonexistent" }]
   }
   ```

3. **Type Mismatch**

   ```json
   // ❌ BAD - MENU config for PROMPT node
   {
     "type": "PROMPT",
     "config": {
       "source_type": "STATIC",
       "static_options": [...]
     }
   }
   ```

4. **Orphan Nodes (Unreachable Nodes)**

   ```json
   // ❌ BAD - node_orphan never referenced in any route (has no parent)
   {
     "start_node_id": "node_start",
     "nodes": {
       "node_start": {
         "routes": [{"condition": "true", "target_node": "node_next"}]
       },
       "node_next": {
         "type": "END"
       },
       "node_orphan": {
         // ❌ ERROR: This node has no parent (nothing routes to it)
         // Only start_node_id is allowed to have no parent
         "routes": [{"condition": "true", "target_node": "node_next"}]
       }
     }
   }

   // ✅ GOOD - All non-start nodes have parents
   {
     "start_node_id": "node_start",
     "nodes": {
       "node_start": {
         "routes": [{"condition": "true", "target_node": "node_next"}]
       },
       "node_next": {
         // ✅ Has parent (node_start routes to it)
         "routes": [{"condition": "true", "target_node": "node_end"}]
       },
       "node_end": {
         // ✅ Has parent (node_next routes to it)
         "type": "END"
       }
     }
   }
   ```

5. **Missing Catch-All Route**

   ```json
   // ❌ BAD - No catch-all route, flow will crash if conditions don't match
   {
     "type": "LOGIC_EXPRESSION",
     "routes": [
       { "condition": "context.status == 'active'", "target_node": "node_active" },
       { "condition": "context.status == 'inactive'", "target_node": "node_inactive" }
       // What if status is 'pending'? Flow terminates with error!
     ]
   }

   // ✅ GOOD - Always include catch-all route
   {
     "type": "LOGIC_EXPRESSION",
     "routes": [
       { "condition": "context.status == 'active'", "target_node": "node_active" },
       { "condition": "context.status == 'inactive'", "target_node": "node_inactive" },
       { "condition": "true", "target_node": "node_default" }  // ✅ Catch-all
     ]
   }
   ```

6. **Duplicate Route Conditions**

```json
// ❌ BAD - Duplicate route conditions
{
  "type": "LOGIC_EXPRESSION",
  "routes": [
    { "condition": "context.status == 'active'", "target_node": "node_active" },
    { "condition": "true", "target_node": "node_default_1" },
    { "condition": "TRUE", "target_node": "node_default_2" }  // ✗ Duplicate: "true" === "TRUE"
  ]
}

// ✅ GOOD - Unique route conditions only
{
  "type": "LOGIC_EXPRESSION",
  "routes": [
    { "condition": "context.status == 'active'", "target_node": "node_active" },
    { "condition": "context.status == 'inactive'", "target_node": "node_inactive" },
    { "condition": "true", "target_node": "node_default" }  // ✓ Single catch-all
  ]
}
```

### Flow Structure Best Practices

#### 1. Naming Conventions

```json
// ✅ GOOD - Clear, descriptive names
"node_check_driver_status"
"node_get_origin_location"
"node_confirm_trip_details"

// ❌ BAD - Cryptic abbreviations
"node_chk_drv"
"node_loc1"
"node_conf"
```

#### 2. Variable Naming

```json
// ✅ GOOD - Descriptive names
"driver_name"
"departure_time"
"available_seats"

// ❌ BAD - Unclear names
"dn"
"dt"
"seats"
```

#### 3. Flow Organization

```json
// ✅ GOOD - Logical grouping with comments
{
  "nodes": {
    // Authentication nodes
    "node_check_user": { ... },
    "node_login": { ... },

    // Data collection nodes
    "node_get_name": { ... },
    "node_get_email": { ... },

    // Processing nodes
    "node_save_data": { ... },
    "node_send_confirmation": { ... }
  }
}
```

#### 4. Route Ordering

```json
// ✅ GOOD - Specific conditions first, catch-all last
"routes": [
  { "condition": "selection == 1", "target_node": "node_option1" },
  { "condition": "selection == 2", "target_node": "node_option2" },
  { "condition": "selection > 0", "target_node": "node_valid" },
  { "condition": "true", "target_node": "node_error" }
]
```

#### 5. Error Handling

```json
// ✅ GOOD - Always handle errors
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_next" },
    { "condition": "error", "target_node": "node_error_handler" }
  ]
}

// ❌ BAD - No error route
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_next" }
  ]
}
```

### Complete Flow Example

See the Tujane driver flow in [`flows/tujane_driver_flow_v1.json`](flows/tujane_driver_flow_v1.json) for a complete, working example demonstrating:

- All node types
- Complex routing
- Dynamic menus
- API integration
- Validation
- Error handling

---

## 2. Core Capabilities

### ✅ Supported Features

1. **Multi-Step Conversations**

   - Sequential data collection through PROMPT nodes
   - Complex branching based on user input and context
   - Session state persistence across interactions

2. **Dynamic Content**

   - Template-based message rendering with `{{variable}}` syntax
   - Context variable access and manipulation
   - Dynamic menu generation from arrays

3. **External Integration**

   - HTTP API calls (GET, POST, PUT, DELETE, PATCH)
   - Response data mapping to context variables
   - Success/failure routing based on API responses

4. **Input Validation**

   - Regex pattern matching
   - JavaScript-style expression validation
   - Custom error messages
   - Retry logic with attempt limits

5. **User Navigation**
   - Interrupt keywords (e.g., "0" to go back)
   - Menu-based selection
   - Conditional flow routing

---

## 3. System Constraints

### 🔒 Hard Limits

| Constraint                 | Limit                                        | Reason                        |
| -------------------------- | -------------------------------------------- | ----------------------------- |
| **Flow Execution**         |
| Max auto-progression steps | 10 consecutive nodes without user input      | Prevent infinite loops        |
| Session timeout            | 30 minutes (absolute, from session creation) | Resource management           |
| API request timeout        | 30 seconds (fixed)                           | Prevent hanging requests      |
| Max validation attempts    | 3 (configurable via flow defaults)           | Prevent abuse                 |
| **Input Sanitization**     |
| User input length          | 4096 characters per message (truncated)      | Prevent DoS attacks           |
| **Flow Structure**         |
| Nodes per flow             | 48                                           | Performance & maintainability |
| Routes per node            | 8                                            | Complexity management         |
| Flow ID length             | 96 characters                                | Database limits               |
| Node ID length             | 96 characters                                | Database limits               |
| Variable name length       | 96 characters                                | Database limits               |
| Variable default - string  | 256 characters                               | Initialization values         |
| Variable default - number  | Standard JSON number                         | No special limit              |
| Variable default - boolean | true/false                                   | No special limit              |
| Variable default - array   | 24 items max                                 | Matches runtime limit         |
| **Bot Entity**             |
| Bot name length            | 96 characters                                | Branding & display            |
| Bot description length     | 512 characters                               | Optional metadata             |
| **Content Limits**         |
| Message text length        | 1024 characters                              | SMS/messaging limits          |
| Error message length       | 512 characters                               | User experience               |
| Template length            | 1024 characters                              | Processing limits             |
| Counter text length        | 512 characters                               | User feedback                 |
| Interrupt keyword length   | 96 characters                                | Navigation keywords           |
| **Mappings**               |
| Source path length         | 256 characters                               | Dot notation paths            |
| **Menu Options**           |
| Static options count       | 8                                            | User experience               |
| Dynamic options count      | 24 (first 24 if source exceeds)              | Performance & UX              |
| Option label length        | 96 characters                                | Display limits                |
| **Validation**             |
| Regex pattern length       | 512 characters                               | Processing time               |
| Expression length          | 512 characters                               | Processing time               |
| Route condition length     | 512 characters                               | Same as expression limit      |
| Max retry attempts         | 10 (default: 3)                              | Configurable per flow         |
| **Context & Session**      |
| Context size (total)       | 100 KB                                       | Memory management             |
| Array length in context    | 24 items per array variable (truncated if exceeded) | Performance                   |
| Max concurrent sessions    | Unlimited                                    | Limited by system memory      |
| **API Requests**           |
| Request URL length         | 1024 characters                              | HTTP limits                   |
| Request body size          | 1 MB                                         | API limits                    |
| Response body size         | 1 MB                                         | Memory & performance          |
| Max headers per request    | 10                                           | Complexity management         |
| Header name length         | 128 characters                               | HTTP standards                |
| Header value length        | 2048 characters                              | Tokens & long values          |

**Notes**:

- Auto-progression counter resets at PROMPT or MENU nodes (user input required)
- Session timeout is absolute (30 minutes from creation, not last activity)
- Limits enforced during flow validation and runtime execution
- Input sanitization (4096 chars): Applied automatically at webhook ingestion. Truncation logged but user not notified. See Section 10.1 for complete sanitization rules.
- Array length limit (24 items): Enforced whenever an array is written to context (defaults, API responses, MENU mappings). Arrays exceeding 24 items are silently truncated to first 24 items.
- Source path notation: Only dot notation supported (e.g., `data.items.0.name`). Bracket notation (e.g., `items[0]`) NOT supported. Root array/primitive access requires `*` prefix (e.g., `*`, `*.0`, `*.0.field`).

### ⚠️ Design Constraints

1. **Single-Threaded Processing**

   - One message processed at a time per session
   - No parallel node execution
   - Sequential flow only

2. **Stateless Nodes**

   - Nodes cannot maintain internal state between executions
   - All state must be in session context
   - Node processors are reused across sessions

3. **Template Rendering Scope**
   - Templates only have access to current context
   - No access to previous messages
   - No cross-session data access

---

## 4. Node Type Specifications

### PROMPT Node

**Purpose**: Collect and validate user input

**Capabilities**:

- ✅ Display templated message
- ✅ Wait for user input
- ✅ Validate input with regex or expressions
- ✅ Save validated input to context
- ✅ Handle interrupts (navigation keywords checked before validation)
- ✅ Show retry messages with attempt counters
- ✅ Empty input handling through validation

**Constraints**:

- ❌ Cannot execute without user input
- ❌ Cannot skip validation if defined
- ❌ Cannot save multiple variables from one input
- ❌ Must have `save_to_variable` defined

**Empty Input Handling**:

**System Behavior**: The system automatically trims leading and trailing whitespace from user input before processing. Whitespace-only input becomes an empty string.

**Processing Order**:

1. Trim leading/trailing whitespace from user input
2. Check for interrupt match (exact match, case-insensitive)
3. If interrupt matches → route immediately (bypass all validation)
4. If no interrupt → check empty/required rule
5. If not empty → run validation
6. If validation passes → save to variable

**Default Behavior**: Empty input is **ALWAYS REJECTED unless explicitly allowed in validation**

**Interrupt Restrictions**:

- Empty string `""` is NOT allowed as an interrupt keyword (reserved for system empty handling)
- Maximum length: 96 characters
- Whitespace in interrupt keywords allowed: `"go back"`, `"cancel order"`
- Interrupt keywords are trimmed before matching
- Case-insensitive matching applied
- Multi-word interrupts supported

**Interrupt Behavior**:

- Bypasses all validation checks
- Does not save to variable
- Does not count as retry attempt
- Routes immediately to target_node
- Can be any non-empty string (even if it would fail validation)

**When No Validation Defined**:

```json
{
  "type": "PROMPT",
  "config": {
    "text": "What's your name?",
    "save_to_variable": "name"
    // No validation defined
  }
}
```

- User submits empty input → **REJECTED**
- Error message: "This field is required. Please enter a value."
- Counts toward retry attempts
- After max attempts → routes to fail_route or terminates

**When Validation Defined (but doesn't check for empty)**:

```json
{
  "validation": {
    "type": "EXPRESSION",
    "rule": "input.isAlpha()", // No empty check
    "error_message": "Please enter letters only"
  }
}
```

- Empty input: `"".isAlpha()` returns `false`
- Validation fails → retry

**To explicitly allow empty input (optional fields)**:

```json
{
  "validation": {
    "type": "EXPRESSION",
    "rule": "input.length == 0 || (input.isNumeric() && input.length == 10)",
    "error_message": "Enter 10-digit phone or leave empty to skip"
  }
}
```

- Empty input: `"".length == 0` → true → validation passes
- Saved as empty string ""

**To explicitly require non-empty input**:

```json
{
  "validation": {
    "type": "EXPRESSION",
    "rule": "input.length > 0 && input.isAlpha()",
    "error_message": "This field is required and must contain only letters"
  }
}
```

**Key Principle**: Fields are required by default. Optional fields must explicitly allow empty input in validation rules.

**When to Use**:

- Collecting user information (name, location, time)
- Getting confirmation (yes/no answers)
- Requesting specific formatted input (phone, email)
- Optional fields (with appropriate validation)

**When NOT to Use**:

- Displaying information only (use TEXT)
- Branching logic without input (use LOGIC_EXPRESSION)
- Selecting from options (use MENU)

---

### MENU Node

**Purpose**: Present options and capture user selection

**Capabilities**:

- ✅ Static options (hardcoded list)
- ✅ Dynamic options (from context arrays)
- ✅ Template-based option formatting
- ✅ Extract multiple values from selected item
- ✅ Numeric selection (1, 2, 3...)
- ✅ Interrupt support (same as PROMPT nodes)
- ✅ Invalid selection handling with retry limits

**Constraints**:

- ❌ **Cannot mix static and dynamic** - must choose either STATIC or DYNAMIC source_type
- ✅ **Interrupts checked first** before selection validation
- ❌ Cannot have non-numeric selection methods
- ❌ Selection validation limited to numeric range check only
- ❌ Dynamic source must be an array in context
- ❌ Output mapping only works with dynamic options
- ❌ **Static menus limited to 8 options maximum**
- ❌ **Dynamic menus limited to 24 options** - if source array exceeds 24, only first 24 items displayed

**Invalid Selection Handling**:

When user enters invalid selection (out of range, non-numeric, etc.):

1. Display configurable error message (or default: "Invalid selection. Please choose a valid option.")
2. Re-display menu options
3. Wait for new input
4. Count toward max attempts limit (from flow defaults)
5. After max attempts: route to fail_route or terminate flow

**Interrupt Behavior**:

- Interrupts are checked **before** menu validation
- If input matches an interrupt, routes to interrupt target immediately
- Bypasses menu selection validation entirely
- Does not count as invalid selection attempt

**⚠️ Interrupt vs Selection Conflicts**:

**Priority**: Interrupts **ALWAYS WIN** over valid menu selections

**Problematic Pattern**:

```json
{
  "static_options": [
    { "label": "Option 1" },
    { "label": "Option 2" },
    { "label": "Option 3" },
    { "label": "Go back" } // This is option 4
  ],
  "interrupts": [
    { "input": "4", "target_node": "node_cancel" } // ❌ CONFLICT!
  ]
}
```

- User enters "4" → Interrupt triggers → Routes to node_cancel
- User **CANNOT** select option 4 (interrupt intercepts it)

**Best Practices**:

- Use non-numeric interrupts: "0", "back", "cancel" (not "1", "2", etc.)
- Keep interrupts outside menu selection range (1-8)
- Use descriptive text keywords instead of numbers
- Communicate interrupts clearly to users

**Recommended Pattern**:

```json
{
  "type": "MENU",
  "config": {
    "text": "Select a trip:\n\n[Options listed here]\n\nOr enter 0 to cancel",
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.from}} → {{item.to}}",
    "interrupts": [
      { "input": "0", "target_node": "node_cancel" }, // ✅ Outside range
      { "input": "back", "target_node": "node_previous" } // ✅ Text keyword
    ],
    "error_message": "Invalid selection. Please enter a valid number from the list above."
  }
}
```

**When to Use**:

- Presenting multiple choices to user
- Selecting from database records (trips, products)
- Yes/No confirmations with clear options

**When NOT to Use**:

- Free-text input (use PROMPT)
- Conditional branching without user input (use LOGIC_EXPRESSION)

---

### API_ACTION Node

**Purpose**: Execute external HTTP requests

**Capabilities**:

- ✅ HTTP methods: GET, POST, PUT, DELETE, PATCH
- ✅ Template-based URL and body
- ✅ Custom headers
- ✅ Response data extraction with path notation
- ✅ Success/failure routing
- ✅ Type conversion (STRING, NUMBER, BOOLEAN, ARRAY)

**Constraints**:

- ❌ No retry logic (implement in API or use multiple nodes)
- ⚙️ **Fixed request timeout: 30 seconds** (not configurable)
- ✅ Timeout triggers `error` route condition
- ❌ No file upload support
- ⚠️ Response body size limit: 1 MB (system-wide)
- ⚠️ Request body size limit: 1 MB (system-wide)
- ⚠️ Headers limit: Maximum 10 headers per request
- ⚠️ Header name: Maximum 128 characters
- ⚠️ Header value: Maximum 2048 characters
- ❌ Must complete before flow continues
- ❌ Cannot abort mid-request
- ✅ **JSON-only responses**: Non-JSON responses route to `error` condition
- ✅ **Request body type preservation**: Template variables in request body preserve their native JSON types. Numbers, booleans, and arrays are rendered with proper JSON types (not converted to strings). Type is determined by the variable's declared type in flow definition, or inferred from the actual value if no type is declared.

**Request Body Type Preservation**:

When rendering template variables in JSON request bodies, the system preserves native JSON types:

**Type Resolution Order**:

1. **Check flow variable type definition** (if variable declared in flow)
2. **Infer from actual value type** (if no type declared)
3. **Preserve as-is** for arrays

**Type Preservation Examples**:

```json
// Flow variables definition
"variables": {
  "fee_amount": { "type": "NUMBER", "default": 0 },
  "is_premium": { "type": "BOOLEAN", "default": false },
  "user_name": { "type": "STRING", "default": "" }
}

// Request body template
"body": {
  "amount": "{{fee_amount}}",
  "premium": "{{is_premium}}",
  "name": "{{user_name}}"
}

// Context values: fee_amount = 500, is_premium = true, user_name = "Alice"
// Rendered JSON sent to API:
{
  "amount": 500,           // ✅ Number (not "500")
  "premium": true,         // ✅ Boolean (not "true")
  "name": "Alice"          // ✅ String
}
```

**Type Inference Without Declaration**:

```json
// No variable declarations, values set dynamically from API response
// Context: {price: 99.99, active: false, items: ["a", "b"]}

"body": {
  "price": "{{price}}",      // → 99.99 (number inferred)
  "active": "{{active}}",    // → false (boolean inferred)
  "items": "{{items}}"       // → ["a", "b"] (array preserved)
}
```

**String Values Remain Strings**:

```json
// Even if a string contains only digits, it remains a string
// Context: {user_id: "12345", count: 12345}

"body": {
  "user_id": "{{user_id}}",  // → "12345" (string)
  "count": "{{count}}"       // → 12345 (number)
}
```

**Best Practice**: Always declare variable types in flow definition for predictable behavior:

```json
"variables": {
  "amount": { "type": "number" },     // ✅ Explicit type
  "enabled": { "type": "boolean" },   // ✅ Explicit type
  "name": { "type": "string" }        // ✅ Explicit type
}
```

**Response Format Requirements**:

- **Supported Format**: JSON only
- **Content-Type**: Should be `application/json` (recommended but not strictly enforced)
- **Parse Failure**: Routes to `error` condition
- **Empty Response** (HTTP 204 No Content): Routes to `success` if status code matches, response_map skipped

**Parse Behavior**:

```
Success status (200-299) + Valid JSON → success route
Success status + Invalid JSON → error route
Success status + Empty body (204) → success route (response_map skipped)
Error status (400-599) → error route
Timeout (30s) → error route
```

**Not Supported**:

- Plain text responses
- XML responses
- HTML responses (e.g., error pages)
- Binary data (PDF, images, etc.)
- Streaming responses

**Recommendation**: If your API returns non-JSON responses, wrap it in your backend proxy that converts to JSON format.

**Timeout Behavior**:

- Default timeout: **30 seconds**
- After timeout: Triggers `error` route condition
- Not configurable per node or per flow
- System-wide setting

**Example with timeout handling**:

```json
{
  "type": "API_ACTION",
  "config": {
    "request": {
      "method": "POST",
      "url": "https://api.example.com/slow-endpoint"
    }
  },
  "routes": [
    { "condition": "success", "target_node": "node_success" },
    { "condition": "error", "target_node": "node_timeout_or_error" }
  ]
}
```

**Query Parameters in URLs**:

Query parameters can be added using template syntax in the URL:

```json
"request": {
  "method": "GET",
  "url": "https://api.example.com/users?page={{page}}&limit=10&sort=name"
}
```

**Best Practice**: Always include error route to handle timeouts gracefully.

**When to Use**:

- Fetching user data from database
- Submitting form data to backend
- Checking user permissions
- Posting transactions

**When NOT to Use**:

- Long-running processes (use async job patterns, must complete within 30s)
- File uploads
- Streaming data
- WebSocket connections

---

### LOGIC_EXPRESSION Node

**Purpose**: Internal conditional routing

**Capabilities**:

- ✅ Evaluate context variables
- ✅ Array length checks
- ✅ Comparison operators (==, !=, >, <, >=, <=)
- ✅ Logical operators (&&, ||)
- ✅ Null/None checks
- ✅ Multiple route conditions

**Constraints**:

- ❌ Cannot show messages to user
- ❌ Cannot wait for input
- ❌ Cannot modify context
- ❌ No complex computations
- ❌ No function calls
- ❌ Conditions evaluated in order (first match wins)

**Path Navigation Rules**:

**Null-Safe Navigation**:

- Missing properties → return `null` (doesn't cause errors)
- `null` values in path → condition evaluates to `false`
- Empty arrays → accessing index returns `null`
- No depth limit on nested paths

**Supported Syntax**:

- Dot notation: `context.user.profile.age`
- Array index: `context.trips.0.driver` (zero-based, use dot notation)
- Array length: `context.items.length`
- Deep nesting: `context.a.b.c.d.e.f...` (no limit)

**NOT Supported**:

- Bracket notation: `context.trips[0]` ❌ (use `context.trips.0` instead)
- Quoted keys: `context['user']` ❌
- Negative indices: `context.trips.-1` ❌

**Null-Safe Examples**:

```javascript
// context.user = null
"context.user.age > 18"; // → false (null-safe, doesn't error)

// context.trips = []
"context.trips.0.id == '123'"; // → false (empty array, index returns null)

// context = {} (missing property)
"context.missing.path != null"; // → false (missing property)

// Safe chaining
"context.trips.length > 0 && context.trips.0.active == true";
// If trips is empty, first condition false, second not evaluated (short-circuit)
```

**When to Use**:

- Branching based on API results
- Checking if arrays are empty
- Routing based on user type or status
- Implementing if-else logic

**When NOT to Use**:

- Displaying messages (use TEXT)
- Getting user input (use PROMPT)
- Complex calculations (do in API)

---

### Text Node

**Purpose**: Display information and auto-progress

**Capabilities**:

- ✅ Display templated message
- ✅ Auto-progress to next node
- ✅ Access full context for templates

**Constraints**:

- ❌ Cannot wait for user input
- ❌ Cannot validate anything
- ❌ Cannot save to context
- ❌ Must have a next node in routes

**When to Use**:

- Success confirmations
- Error messages
- Informational notifications
- Intermediate status updates

**When NOT to Use**:

- Collecting input (use PROMPT)
- Ending conversation (use END with TEXT before it)
- Waiting for user acknowledgment

---

### END Node

**Purpose**: Terminate conversation

**Capabilities**:

- ✅ Mark session as completed
- ✅ Cleanup session data
- ✅ No further nodes execute

**Constraints**:

- ❌ Cannot show message (use TEXT before END)
- ❌ Cannot route to other nodes
- ❌ Cannot be bypassed once reached
- ❌ Cannot restart flow automatically

**When to Use**:

- Natural conversation completion
- Error termination
- User exit request

**When NOT to Use**:

- Temporary pauses (session stays active)
- Conditional endings (use routes to END)

---

## 5. Templating System

### Supported Patterns

| Pattern          | Example                | Result                                                 |
| ---------------- | ---------------------- | ------------------------------------------------------ |
| Flow variable    | `{{name}}`             | "John"                                                 |
| Nested object    | `{{user.email}}`       | "john@example.com"                                     |
| Array index      | `{{items.0}}`          | First item (literal template if invalid/out of bounds) |
| Item property    | `{{item.id}}`          | "trip_123" (MENU nodes only)                           |
| Index in loop    | `{{index}}`            | 1, 2, 3... (MENU nodes only)                           |
| User identifier  | `{{user.channel_id}}`  | "+254712345678" (API_ACTION nodes only)                |
| Channel name     | `{{user.channel}}`     | "whatsapp" (API_ACTION nodes only)                     |
| Input            | `{{input}}`            | User's message (PROMPT validation only)                |

**Important**: Do NOT use `{{context.*}}` prefix in templates. Flow variables are accessed directly:
- ✅ Correct: `{{name}}`, `{{user_email}}`, `{{age}}`
- ❌ Wrong: `{{context.name}}`, `{{context.user_email}}`, `{{context.age}}`

**Note**: The `context.` prefix is ONLY used in route conditions and validation expressions, NOT in templates:
- Templates: `"text": "Hello {{name}}!"`
- Conditions: `"condition": "context.age > 18"`

**Nested Objects**:
- Nested paths like `{{user.email}}` work for **rendering text** in all node types
- For **type conversion in API request bodies**, the variable name in flow definitions must match the **last segment** of the path
- Example: For `{{user.age}}`, define variable as `"age": {"type": "NUMBER"}`, not `"user_age"`

### Context Structure Best Practices

**Option 1 - Flat Structure** (Recommended - Simple and explicit):
```json
"variables": {
  "user_name": {"type": "STRING", "default": null},
  "user_email": {"type": "STRING", "default": null},
  "user_age": {"type": "NUMBER", "default": 0}
}

// Runtime context (variables stored at root level):
{
  "user_name": "Alice",
  "user_email": "alice@example.com",
  "user_age": 25
}

// Templates (access variables directly):
"text": "Hello {{user_name}}!"  // ✓ Renders as "Hello Alice!"
"body": {"name": "{{user_name}}", "age": "{{user_age}}"}  // ✓ Types preserved
```

**Option 2 - Nested Structure** (More organized):
```json
"variables": {
  "name": {"type": "STRING", "default": null},     // ← Matches last segment
  "email": {"type": "STRING", "default": null},    // ← Matches last segment
  "age": {"type": "NUMBER", "default": 0}          // ← Matches last segment
}

// Runtime context (nested objects):
{
  "user": {
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25
  }
}

// Templates (access nested properties):
"text": "Hello {{user.name}}!"  // ✓ Renders as "Hello Alice!"
"body": {"age": "{{user.age}}"}  // ✓ Converts to number (25, not "25")
```

**Critical Rule for Type Conversion**:
The variable name in flow definitions must match the **last segment** of the template path:
- Path: `{{user.age}}` → Define variable: `"age"` ✓
- Path: `{{user.age}}` → Define variable: `"user_age"` ✗ (won't find it)

**When to Use Each**:
- **Flat structure**: Clearer variable names, no ambiguity, easier to maintain
- **Nested structure**: More organized context, works if variable names match last segments
- **Deep nesting** (`{{a.b.c.d}}`): Technically supported but harder to maintain

### Template Capabilities

✅ **Supported**:

- Variable substitution
- Nested object access (dot notation)
- Array element access
- Special variables (item, index, user)
- Multiple templates in same string
- Templates in URLs and request bodies
- Type preservation in JSON request bodies (numbers, booleans, arrays)

❌ **Not Supported**:

- Arithmetic operations: `{{count + 1}}`
- String manipulation: `{{name.toUpperCase()}}`
- Conditional rendering: `{{if condition}}`
- Loops: `{{for item in items}}`
- Function calls: `{{formatDate(date)}}`
- Complex expressions: `{{a > b ? c : d}}`
- Default values with `||` operator: `{{name || 'Guest'}}`
  - **Workaround**: Initialize variables with defaults in flow definition
  - **Example**: `"variables": {"name": {"type": "STRING", "default": "Guest"}}`
- **Array `.length` property**: `{{items.length}}`
  - **Important**: `.length` does NOT work in templates (TEXT, MENU, PROMPT text)
  - **Where it DOES work**: LOGIC_EXPRESSION route conditions, PROMPT validation expressions
  - **Workaround**: Store array length as separate variable first

### Array Length Limitation

**Critical Limitation**: The `.length` property is NOT available on arrays in message templates.

**❌ Does NOT Work in Templates**:
```json
{
  "type": "TEXT",
  "config": {
    "text": "You have {{items.length}} items."
  }
}
// Output: "You have {{items.length}} items." (displayed literally)
```

**✅ DOES Work in Conditions**:
```json
{
  "type": "LOGIC_EXPRESSION",
  "routes": [
    {
      "condition": "context.items.length > 0",  // ✓ Works here
      "target_node": "node_has_items"
    }
  ]
}
```

**✅ DOES Work in Validation**:
```json
{
  "type": "PROMPT",
  "config": {
    "validation": {
      "type": "EXPRESSION",
      "rule": "input.length >= 3",  // ✓ Works here
      "error_message": "Minimum 3 characters"
    }
  }
}
```

**Workaround - Store Length as Variable**:
```json
// In API_ACTION, extract array and its length separately:
"response_map": [
  {"source_path": "items", "target_variable": "items"},
  {"source_path": "items.length", "target_variable": "items_count"}
]

// Then use in template:
{
  "type": "TEXT",
  "config": {
    "text": "You have {{items_count}} items."  // ✓ Works
  }
}
```

**Why this limitation exists**: The template engine resolves paths using Python's native attribute/dict access. Python lists don't have a `.length` attribute (they use `len()` function). Only the conditions evaluator has special handling to convert `.length` to `len()`.

### Missing Variable Behavior

When a template references a variable that doesn't exist in context:

**Behavior**: Variable is displayed literally (unreplaced) - intentional debugging feature

**Examples**:

```json
// Template: "Welcome, {{user_name}}!"
// If user_name not set
// Output: "Welcome, {{user_name}}!"

// Template: "Order {{order.id}} confirmed"
// If order is null
// Output: "Order {{order.id}} confirmed"
```

**Why this design**:

- Makes debugging easier - developers see which variables are missing
- No silent failures or runtime errors
- Clear indication of configuration issues

**Best Practice**: Initialize all variables in flow definition with appropriate defaults:

```json
"variables": {
  "user_name": { "type": "STRING", "default": "Guest" },
  "order_id": { "type": "STRING", "default": null }
}
```

### Template Contexts by Node

| Node Type        | Available Variables                   | Notes                                                                                                                                          |
| ---------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| PROMPT           | `{{variable}}`, `{{input}}`           | `input` only in validation expressions                                                                                                         |
| MENU             | `{{variable}}`, `{{item.*}}`, `{{index}}` | `item` and `index` only in `item_template`                                                                                                     |
| API_ACTION       | `{{variable}}`, `{{user.channel_id}}` | `user.channel_id` is the platform-specific user identifier (e.g., phone number for WhatsApp). Other user data should be fetched via API calls. |
| LOGIC_EXPRESSION | N/A (no templates)                    | Routes use expressions, not templates                                                                                                          |
| TEXT          | `{{variable}}`                        | All flow variables available                                                                                                                   |

**Special Variables**:

- `{{user.channel_id}}`: Platform-specific user identifier (e.g., phone number for WhatsApp: "+254712345678", user ID for Slack: "U012345")
- `{{user.channel}}`: Channel name (e.g., "whatsapp", "telegram", "slack")
- `{{item.*}}`: Current item in MENU dynamic template (e.g., `{{item.id}}`, `{{item.name}}`)
- `{{index}}`: 1-based counter in MENU dynamic template (1, 2, 3...)
- `{{input}}`: User's input text (only in PROMPT validation expressions)
- `{{current_attempt}}`: Current retry attempt (only in retry counter_text)
- `{{max_attempts}}`: Maximum attempts (only in retry counter_text)

**Variable Availability Summary**:

- Retry counter variables (`current_attempt`, `max_attempts`) are **only** available in `defaults.retry_logic.counter_text`
- They are **not** available in error messages, validation rules, or session context

---

## 6. Validation System

### REGEX Validation

**Capabilities**:

- ✅ Full regex pattern matching
- ✅ Case-sensitive and insensitive
- ✅ Character classes, quantifiers, groups
- ✅ Anchors (^, $)

**Constraints**:

- ⚠️ **Must match entire input string**
  - The regex engine matches against the **complete user input** from start to finish
  - Patterns are treated as if wrapped with implicit anchors: `/^pattern$/`
  - If the pattern matches any substring, but not the entire input, validation **fails**
  - **Always use explicit anchors (^, $) for clarity** even though they're implicit
  - Example: Pattern `[0-9]+` for input "123abc" → **FAILS** (digits match but "abc" remains unmatched)
  - Example: Pattern `^[0-9]+$` for input "123" → **PASSES** (entire input matched)
- ❌ No lookahead/lookbehind support
- ❌ No named groups
- ❌ Cannot access captured groups in error message

**Full String Match Behavior**:

```javascript
// User input: "abc123def"
"[0-9]+"; // NO MATCH (looks for digits, but "abc" at start fails entire match)
"^[0-9]+$"; // NO MATCH (explicit: only digits allowed) ✅ RECOMMENDED
".*[0-9]+.*"; // MATCH (allows anything before/after digits)

// User input: "123"
"[0-9]+"; // MATCH (entire string is digits)
"^[0-9]+$"; // MATCH (same, but explicit) ✅ RECOMMENDED
"[0-9]{3}"; // MATCH (exactly 3 digits)

// User input: "hello"
"hello"; // MATCH (exact match)
"^hello$"; // MATCH (explicit exact match) ✅ RECOMMENDED
"hell"; // NO MATCH (must match entire string)
```

**Best Practice Examples** - Always use anchors:

```javascript
"^[A-Z][a-z]+$"; // Capital first letter + lowercase letters
"^\\d{4}-\\d{2}-\\d{2}$"; // Date format YYYY-MM-DD
"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"; // Email
"^\\+?[0-9]{10,15}$"; // Phone number (optional +, 10-15 digits)
```

### EXPRESSION Validation

**Capabilities**:

- ✅ JavaScript-style methods: `input.isAlpha()`, `input.isNumeric()`, `input.isDigit()`
- ✅ String length: `input.length`
- ✅ Numeric comparisons: `input > 0`, `input <= 100`
- ✅ Context variable access: `context.max_value`
- ✅ Logical operators: `&&`, `||`
- ✅ Type checking: numeric vs string handled automatically

**Constraints**:

- ❌ No custom functions
- ❌ No string methods beyond isAlpha/isNumeric/isDigit
- ❌ No array/object methods
- ❌ No date/time operations
- ❌ Limited to simple boolean expressions

**Supported Methods**:

```javascript
input.isAlpha(); // Only letters (a-z, A-Z)
input.isNumeric(); // Accepts: optional minus sign, digits, optional decimal point
// Examples: "123", "-45", "12.34", ".5"
// Rejects: "1e10", "1.2.3", "--5", scientific notation
input.isDigit(); // Only digits (0-9)
input.length; // String length
```

**Examples**:

```javascript
// Valid expressions
"input.isAlpha() && input.length >= 3";
"input.isNumeric() && input > 0 && input <= context.capacity";
"input.length >= 5 && input.length <= 20";

// Invalid expressions
"input.toUpperCase() === 'YES'"; // ❌ toUpperCase not supported
"input.includes('test')"; // ❌ includes not supported
"parseInt(input) > 0"; // ❌ parseInt not supported
```

---

## 7. Routing & Logic

### Route Condition Types

| Type          | Example                                | Description             |
| ------------- | -------------------------------------- | ----------------------- |
| Keyword       | `"success"`                            | Checks success flag     |
| Keyword       | `"error"`                              | Checks error flag       |
| Keyword       | `"true"`                               | Fallback (catches all)  |
| Comparison    | `"selection == 2"`                     | Integer equality        |
| Comparison    | `"selection != null"`                  | Null check              |
| Context check | `"context.trips.length > 0"`           | Array length            |
| Complex       | `"selection == 1 && context.verified"` | Multiple conditions     |

### Route Condition Validation Rules

The system validates route conditions and counts based on node type to prevent invalid configurations at design time.

**Implementation**: [`route_validator.py`](v1/app/core/route_validator.py:1), [`flow_validator.py`](v1/app/core/flow_validator.py:595-610), [`constants.py`](v1/app/utils/constants.py:151-156)

#### Node-Specific Routing Rules

| Node Type            | Allowed Conditions                             | Max Routes      | Notes                                          |
| -------------------- | ---------------------------------------------- | --------------- | ---------------------------------------------- |
| **PROMPT**           | `"true"` only                                  | 1               | Single progression route                       |
| **TEXT**          | `"true"` only                                  | 1               | Single progression route                       |
| **MENU (STATIC)**    | `"selection == N"` (N ≤ num_options), `"true"` | num_options + 1 | N must be within 1 to number of options        |
| **MENU (DYNAMIC)**   | `"true"` only                                  | 1               | **Critical: Only single "true" route allowed** |
| **API_ACTION**       | `"success"`, `"error"`, `"true"`               | 3               | All conditions optional                        |
| **LOGIC_EXPRESSION** | Any valid expression                           | 8               | No syntax restrictions                         |
| **END**              | None                                           | 0               | Terminal node                                  |

#### MENU Node Routing (DYNAMIC vs STATIC)

**Critical Distinction**: DYNAMIC and STATIC menus have completely different routing patterns.

**STATIC MENU** - Route by specific selections:

```json
{
  "config": {
    "source_type": "STATIC",
    "static_options": [{ "label": "M-Pesa" }, { "label": "Card" }]
  },
  "routes": [
    { "condition": "selection == 1", "target_node": "node_mpesa" }, // ✅ Valid
    { "condition": "selection == 2", "target_node": "node_card" }, // ✅ Valid
    { "condition": "true", "target_node": "node_error" } // ✅ Fallback
  ]
}
```

**DYNAMIC MENU** - Single route only:

```json
{
  "config": {
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "output_mapping": [{ "source_path": "id", "target_variable": "trip_id" }]
  },
  "routes": [
    { "condition": "true", "target_node": "node_logic" } // ✅ Single route
  ]
}
```

**Why DYNAMIC Restriction**: Options unknown at design time. Use LOGIC_EXPRESSION after menu for conditional routing:

```json
"node_menu": {
  "type": "MENU",
  "config": { "source_type": "DYNAMIC", /* ... */ },
  "routes": [{ "condition": "true", "target_node": "node_logic" }]
},
"node_logic": {
  "type": "LOGIC_EXPRESSION",
  "routes": [
    { "condition": "context.trip_id == 'express'", "target_node": "node_express" },
    { "condition": "true", "target_node": "node_standard" }
  ]
}
```

#### Common Validation Errors

**Error: Invalid condition for node type**

```json
// ❌ PROMPT with selection condition
{ "type": "PROMPT", "routes": [{ "condition": "selection == 1", ... }] }
// Error: "PROMPT nodes only allow condition 'true'"

// ❌ DYNAMIC MENU with selection routing
{ "config": { "source_type": "DYNAMIC" }, "routes": [{ "condition": "selection == 1", ... }] }
// Error: "DYNAMIC MENU nodes only allow condition 'true'"
```

**Error: Route count exceeded**

```json
// ❌ DYNAMIC MENU with multiple routes
{
  "config": { "source_type": "DYNAMIC" },
  "routes": [
    /* 2 routes */
  ]
}
// Error: "DYNAMIC MENU nodes can only have 1 route"
// Suggestion: "Use a LOGIC_EXPRESSION node after the menu for conditional routing"
```

**Error: Selection out of range**

```json
// ❌ STATIC MENU - selecting beyond available options
{
  "config": { "source_type": "STATIC", "static_options": [/* 3 options */] },
  "routes": [{ "condition": "selection == 5", ... }]  // Only 3 options!
}
// Error: "Selection number 5 is out of range. Valid range is 1-3"
```

#### Best Practices

1. **DYNAMIC menus**: Always use pattern `DYNAMIC MENU → LOGIC_EXPRESSION → routes`
2. **API_ACTION**: Include both `success` and `error` routes
3. **STATIC menus**: Validate selection numbers match option count
4. **Always**: Include `"true"` fallback as final route in LOGIC_EXPRESSION nodes

### Runtime Route Sorting

**Automatic Sorting**: Routes are automatically sorted by priority at runtime before evaluation to ensure optimal route evaluation order.

**Implementation**: The conversation engine sorts routes dynamically when evaluating each node, using the same logic as the frontend route editor.

**Sorting Rules (Lower Priority = Evaluated First)**:

| Node Type            | Condition Pattern  | Priority | Example                         |
| -------------------- | ------------------ | -------- | ------------------------------- |
| **ALL**              | `"true"`           | 1000     | Catch-all always evaluated last |
| **MENU**             | `"selection == N"` | N        | `"selection == 1"` → priority 1 |
| **MENU**             | Other conditions   | 500      | Custom conditions               |
| **API_ACTION**       | `"success"`        | 1        | Success checked first           |
| **API_ACTION**       | `"error"`          | 2        | Error checked second            |
| **API_ACTION**       | Other conditions   | 500      | Custom conditions               |
| **LOGIC_EXPRESSION** | Any condition      | 500      | Maintains definition order      |
| **Other nodes**      | Any condition      | 500      | Default priority                |

**Key Benefits**:

- ✅ Specific conditions always evaluated before catch-all
- ✅ Works for all flows (including old ones without sorted routes)
- ✅ No modification to stored flow data
- ✅ Consistent with frontend behavior
- ✅ Prevents routing issues from route definition order

**Examples**:

```python
# Original routes (as defined in flow)
routes = [
    {"condition": "true", "target_node": "fallback"},
    {"condition": "selection == 1", "target_node": "option1"},
    {"condition": "selection == 2", "target_node": "option2"}
]

# After runtime sorting (for MENU node)
sorted_routes = [
    {"condition": "selection == 1", "target_node": "option1"},  # Priority: 1
    {"condition": "selection == 2", "target_node": "option2"},  # Priority: 2
    {"condition": "true", "target_node": "fallback"}            # Priority: 1000
]

# API_ACTION example
routes = [
    {"condition": "true", "target_node": "fallback"},
    {"condition": "error", "target_node": "error_handler"},
    {"condition": "success", "target_node": "next"}
]

# After runtime sorting
sorted_routes = [
    {"condition": "success", "target_node": "next"},            # Priority: 1
    {"condition": "error", "target_node": "error_handler"},     # Priority: 2
    {"condition": "true", "target_node": "fallback"}            # Priority: 1000
]
```

**Implementation Note**: Sorting happens transparently at runtime. Flow developers don't need to manually order routes - the system ensures optimal evaluation order automatically.

### Routing Capabilities

✅ **Supported**:

- Multiple routes per node
- First-match wins (routes evaluated in order after sorting)
- Automatic route prioritization at runtime
- Context variable access
- Selection value checking (MENU)
- Success/error states (API_ACTION)
- Null/None checks
- Array length checks
- Logical AND (&&) and OR (||)

❌ **Not Supported**:

- Fallback/default routes (use `"condition": "true"` as last route)
- Priority/weight-based routing
- Probabilistic routing
- Time-based routing
- External condition evaluation
- Regular expressions in conditions

### Condition Evaluation Rules

1. **Order Matters**: Routes evaluated top-to-bottom
2. **First Match Wins**: Only first matching route executed
3. **No Fallthrough**: Cannot execute multiple routes
4. **Type Coercion Rules**:
   - `null` in JSON converts to `None` in expressions
   - **No automatic type coercion** between string/number/boolean
   - String vs number comparison **fails** (route doesn't match)
   - Developers must ensure correct types via API response mapping
5. **Context Access**: `context.variable` replaced with actual value before evaluation

### Type Coercion in Comparisons

**No Automatic Type Conversion**:

- Comparisons use strict type checking
- `"123" > 18` → **FAILS** (string vs number)
- `"true" == true` → **FAILS** (string vs boolean)
- `null == "null"` → **FAILS** (null vs string)

**Ensuring Correct Types**:

1. **API Response Mapping** (recommended):

```json
// First, declare variables with correct types
"variables": {
  "age": { "type": "NUMBER", "default": 0 },
  "verified": { "type": "BOOLEAN", "default": false }
}

// Then use response_map (type inference automatic)
"response_map": [
  {
    "source_path": "age",
    "target_variable": "age"  // Will convert to number (from variables)
  },
  {
    "source_path": "verified",
    "target_variable": "verified"  // Will convert to boolean (from variables)
  }
]
```

2. **Validation in PROMPT**:

```json
{
  "validation": {
    "type": "EXPRESSION",
    "rule": "input.isNumeric()", // Ensures numeric format
    "error_message": "Enter a number"
  }
}
```

**Comparison Examples**:

```javascript
// Assuming age collected as string from PROMPT
context.age = "25"; // string (before type conversion)

("context.age > 18"); // FAILS (string vs number comparison returns false)
("context.age == '25'"); // WORKS (string vs string)

// After PROMPT type conversion with declared type: "number"
context.age = 25; // number (after successful conversion)

("context.age > 18"); // WORKS (number vs number)
("context.age == 25"); // WORKS (number vs number)

// Example with MENU selection (always number)
context.selection = 2; // number (automatically set by MENU)

("context.selection == 2"); // WORKS (number vs number)
("context.selection == '2'"); // FAILS (number vs string)
("context.selection > 1"); // WORKS (number vs number)
```

### Type Mismatch Behavior

**Null-Safe Evaluation**:

When comparing values of mismatched types, the system evaluates safely without throwing errors:

- **String vs Number**: Comparison returns `false` (route doesn't match, moves to next route)
- **String vs Boolean**: Comparison returns `false`
- **Integer vs String**: Comparison returns `false`
- **Null comparisons**: `null == null` returns `true`; `null == <any value>` returns `false`
- **Missing properties**: Treated as `null` in comparisons

**Behavior**:

- No exceptions are thrown
- Route simply doesn't match, evaluation continues to next route
- If no routes match, flow terminates with error (see No-Match Route Behavior below)

**Examples**:

```javascript
// Context values
context.age = "25"; // string
context.count = 10; // number
context.flag = true; // boolean
context.missing = null; // null value

// Type mismatch comparisons
("context.age == 25"); // false (string "25" != number 25)
("context.count == '10'"); // false (number 10 != string "10")
("context.flag == 'true'"); // false (boolean true != string "true")
("context.missing == null"); // true (null matches null)
("context.missing != null"); // false
("context.undefined_var == null"); // true (missing property treated as null)

// Safe chaining with type mismatches
("context.age > 18 || context.count > 5"); // false || true = true
// Even though first comparison fails due to type mismatch, second succeeds
```

**Best Practices**:

1. Declare variables with correct types in flow's `variables` section
2. Type inference handles conversion automatically in response_map and output_mapping
3. Be aware that MENU `selection` is always a number
4. Test routes with expected data types during development

### No-Match Route Behavior

**Critical**: If no route condition evaluates to true, the flow terminates with error.

**Behavior**:

1. Flow execution stops immediately
2. User sees error message: "An error occurred. Please try again."
3. Session ends
4. No further nodes execute

**Best Practice**: Always include a catch-all route as the last option:

```json
"routes": [
  { "condition": "specific_check", "target_node": "node_a" },
  { "condition": "another_check", "target_node": "node_b" },
  { "condition": "true", "target_node": "node_default" }  // ✅ Catch-all
]
```

**Example Error Scenario**:

```json
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_success" }
  ]
  // ❌ BAD: No error route! If API fails, flow terminates with error
}

// ✅ GOOD: Always handle all possible outcomes
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_success" },
    { "condition": "error", "target_node": "node_error_handler" },
    { "condition": "true", "target_node": "node_unexpected" }
  ]
}
```

---

## 8. Session Management

### Session Lifecycle

```
User sends message via webhook
    ↓
Create Session (ACTIVE)
    ↓
Process nodes → Update context → Move to next node
    ↓
(Repeat until END node)
    ↓
Mark Session (COMPLETED)
    ↓
Session expires after 30min or explicit delete
```

### Session Behavior

**Session Storage**: Database persistence - sessions survive server restarts

**Session Key Format**: `channel:channel_user_id:bot_id`

**Examples**:

- `"whatsapp:+254712345678:bot_abc123"`
- `"whatsapp:5521999999999:bot_restaurant"`

**Why This Format**:

- ✅ Supports multiple channels (WhatsApp, Telegram, Slack, etc.)
- ✅ Same user can interact with multiple bots simultaneously
- ✅ Each bot maintains isolated sessions
- ✅ Future-proof for multi-channel expansion

**Session Limits**:

- ✅ One active session per user per bot per channel
- ✅ Same user CAN have multiple sessions (one per bot)
- ✅ Same user CAN have multiple sessions (one per channel)
- ❌ Cannot pause/resume sessions
- ⚠️ **Starting new flow in same bot terminates old session silently** - When user triggers a new flow (via trigger keyword) while already in an active session, the old session is immediately deleted and replaced. No warning shown - this is intentional for simplicity. Flow designers should use interrupts within flows for safe navigation.

**Session Timeout**:

- ✅ **Absolute timeout**: 30 minutes from session creation
- ❌ Not a sliding window (doesn't reset on activity)
- ❌ Not configurable per flow
- After timeout: Session marked as EXPIRED, cannot resume

**Example Timeline**:

```
10:00 AM - User starts flow (session created)
10:15 AM - User sends message (session still active, 15 min remaining)
10:30 AM - Session expires (30 min from start)
10:31 AM - User sends message → Message REJECTED, error shown
```

**Post-Expiry Behavior**:
- Messages sent after expiration are **rejected** (not processed)
- User receives: "Session expired. Please start again."
- To start new session: User must send a **trigger keyword**
- No grace period (strict 30-minute cutoff from session creation)

**Session Termination Scenarios**:

1. END node reached → COMPLETED status
2. 30 minutes elapsed → EXPIRED status
3. New flow triggered → Old session deleted silently, new ACTIVE session created
4. No route match → ERROR status, session ends, user sees error message
5. Max auto-progression reached → ERROR status, session ends
6. Max validation attempts exceeded → Routes to fail_route or terminates

### Session Capabilities

✅ **Supported**:

- One active session per user per bot per channel
- Multiple concurrent sessions for same user (different bots or channels)
- Context variables persist across nodes
- Message history tracking
- Validation attempt tracking
- Session timeout (30 minutes, absolute from creation)
- Explicit session reset
- Silent session termination when switching flows within same bot

❌ **Not Supported**:

- Multiple concurrent sessions per user per bot (within same channel)
- Session sharing between users
- Session migration between bots
- Session state snapshots/rollback
- Cross-session data access
- Session pause/resume functionality
- Warning notifications when session is terminated

### Context Variables

**Capabilities**:

- ✅ Store strings, numbers, booleans, arrays
- ✅ Update existing variables
- ✅ Add new variables during flow
- ✅ Pass between nodes
- ✅ Use in templates
- ✅ Use in conditions

**Constraints**:

- ❌ Cannot delete variables (set to null instead)
- ❌ Cannot rename variables
- ❌ No variable type constraints (runtime)
- ❌ No variable lifecycle management
- ❌ No nested update operations (nested objects are immutable once set; use API to reconstruct and reassign entire object)

---

## 9. Error Handling & Termination

### Error Scenarios

| Scenario                        | Behavior                                                     | User Experience                                             |
| ------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| No route matches                | Flow terminates                                              | "An error occurred. Please try again."                      |
| Max auto-progression (10 nodes) | Flow terminates                                              | "System error. Please contact support."                     |
| Max validation attempts         | Route to fail_route or terminate                             | Configurable message or default error                       |
| API timeout (30s)               | Triggers error route                                         | Developer handles via routes                                |
| Session timeout (30 min)        | Session expires                                              | "Session expired. Please start again."                      |
| Invalid flow structure          | Validation error                                             | (Before deployment)                                         |
| Type mismatch in comparison     | Route doesn't match                                          | Continues to next route                                     |
| Template missing variable       | Shows literal `{{variable}}`                                 | No error (debugging feature)                                |
| Empty array in dynamic menu     | Shows menu header with no options; any input will be invalid | Recommend checking array length with LOGIC_EXPRESSION first |
| Invalid menu selection          | Show error, retry                                            | Counts toward max attempts                                  |

### Termination Triggers

**Automatic Termination**:

1. **END node reached** → Session marked COMPLETED
2. **Session timeout (30 min)** → Session marked EXPIRED
3. **No matching route** → Session marked ERROR, terminates immediately
4. **Max auto-progression** → Session marked ERROR after 10 consecutive nodes
5. **Max retry attempts** → Routes to fail_route or terminates if none defined
6. **New flow starts** → Old session deleted silently, new session created

**User Notification**:

- END node: No message (use TEXT node before END for final message)
- Timeout: "Session expired. Please start again."
- No route match: "An error occurred. Please try again."
- Max auto-progression: "System error. Please contact support."
- Max retries: Configurable via fail_route node or default error
- New flow: Silent (no notification to user)

### Best Practices for Error Handling

#### 1. Always Include Error Routes

```json
// ✅ GOOD - Complete error handling
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_success" },
    { "condition": "error", "target_node": "node_error_handler" },
    { "condition": "true", "target_node": "node_unexpected" }
  ]
}

// ❌ BAD - Missing error route
{
  "type": "API_ACTION",
  "routes": [
    { "condition": "success", "target_node": "node_success" }
  ]
  // If API fails, flow terminates with generic error
}
```

#### 2. Use fail_route in Defaults

```json
{
  "defaults": {
    "retry_logic": {
      "max_attempts": 3,
      "fail_route": "node_validation_failed"
    }
  },
  "nodes": {
    "node_validation_failed": {
      "type": "TEXT",
      "config": {
        "text": "We couldn't process your input. Please contact support at +254..."
      },
      "routes": [{ "condition": "true", "target_node": "node_end" }]
    }
  }
}
```

#### 3. Provide Clear Error Messages

```json
{
  "type": "TEXT",
  "config": {
    "text": "❌ We couldn't process your request.\n\nPlease try again or contact support at +254700123456."
  }
}
```

#### 4. Handle Empty Arrays Before Dynamic Menus

```json
{
  "type": "LOGIC_EXPRESSION",
  "routes": [
    {
      "condition": "context.trips.length > 0",
      "target_node": "node_show_menu"
    },
    {
      "condition": "context.trips.length == 0",
      "target_node": "node_no_trips_available"
    },
    {
      "condition": "true",
      "target_node": "node_error"
    }
  ]
}
```

#### 5. Add Catch-All Routes

```json
// Last route in every non-END node
"routes": [
  { "condition": "specific_condition_1", "target_node": "node_a" },
  { "condition": "specific_condition_2", "target_node": "node_b" },
  { "condition": "true", "target_node": "node_fallback" }  // ✅ Catch-all
]
```

### Error Recovery Patterns

#### Pattern 1: Retry with Alternative

```json
{
  "node_api_call": {
    "type": "API_ACTION",
    "routes": [
      { "condition": "success", "target_node": "node_success" },
      { "condition": "error", "target_node": "node_offer_alternative" }
    ]
  },
  "node_offer_alternative": {
    "type": "TEXT",
    "config": {
      "text": "We couldn't complete that action. Would you like to try a different option?"
    },
    "routes": [{ "condition": "true", "target_node": "node_menu_alternatives" }]
  }
}
```

#### Pattern 2: Graceful Degradation

```json
{
  "node_fetch_recommendations": {
    "type": "API_ACTION",
    "routes": [
      {
        "condition": "success && context.recommendations.length > 0",
        "target_node": "node_show_recommendations"
      },
      {
        "condition": "success && context.recommendations.length == 0",
        "target_node": "node_manual_search"
      },
      { "condition": "error", "target_node": "node_manual_search" }
    ]
  }
}
```

#### Pattern 3: Error with Support Escalation

```json
{
  "node_critical_error": {
    "type": "TEXT",
    "config": {
      "text": "We encountered an error processing your request.\n\n📞 Call support: +254700123456\n💬 WhatsApp: +254700123456\n⏰ Available 24/7"
    },
    "routes": [{ "condition": "true", "target_node": "node_end" }]
  }
}
```

### Debugging Tips

1. **Use missing variable behavior**: Undefined variables show as `{{variable}}` in output
2. **Add debug nodes**: Insert TEXT nodes to display context state
3. **Check route order**: First matching route wins, order matters
4. **Verify type conversions**: Use response_map with explicit types
5. **Test error paths**: Manually trigger error conditions during development
6. **Monitor auto-progression**: Add counters to track node chains
7. **Validate flow structure**: Use validation tools before deployment

---

## 10. Security Considerations

### 🔒 Security Best Practices

Security is critical when building conversational flows that handle user data and integrate with external systems. This section outlines key security considerations and best practices.

#### 1. Input Sanitization

**Universal Sanitization Rules (Always Applied)**:

All user input is automatically sanitized by the system. No configuration required.

---

**Layer 1: Baseline Sanitization**

Applied at webhook ingestion, before any processing:

1. **Null bytes removed** (`\x00`)
2. **Control characters removed** (except `\n`, `\t`, `\r`)
3. **Whitespace trimmed** (leading/trailing)
4. **Length limited** (4096 characters maximum, truncated if exceeded)

---

**Layer 2: Context-Aware Escaping**

Applied automatically when data is used:

1. **HTML escaping** - When rendering in web interfaces
2. **JSON escaping** - When building API requests (automatic via JSON encoder)
3. **SQL parameterization** - All database queries use parameterized queries (SQLAlchemy ORM)
4. **URL encoding** - Query parameters automatically percent-encoded

---

**Layer 3: Pattern Rejection**

Automatically rejects input containing dangerous patterns:

- Script tags: `<script>`, `</script>`
- JavaScript protocols: `javascript:`
- Event handlers: `onclick=`, `onerror=`, `onload=`
- Template injection: `{{`, `}}`, `${`, `}`
- Command injection: Multiple commands (`;`, `|`, `&&`)
- Path traversal: `../`, `..\\`
- SQL comments: `--`, `/*`, `*/`

When detected:
- Input rejected with error: "Invalid characters detected. Please try again."
- Counts toward validation retry limit
- After max attempts, routes to `fail_route` or terminates

---

**Processing Order**:

```
1. User sends message
   ↓
2. Layer 1: Baseline sanitization (always)
   ↓
3. Layer 3: Pattern rejection (always)
   ↓
4. PROMPT validation (your regex/expression rules)
   ↓
5. Layer 2: Context-aware escaping (at point of use)
   ↓
6. Data stored/used safely
```

---

**What This Means for Developers**:

- ✅ No sanitization config needed
- ✅ No security fields in flows
- ✅ Protection is automatic
- ✅ Focus only on business validation (email format, date ranges, etc.)

**Example** - You only write validation rules:
```json
{
  "type": "PROMPT",
  "config": {
    "text": "Enter your feedback:",
    "save_to_variable": "feedback",
    "validation": {
      "type": "EXPRESSION",
      "rule": "input.length >= 10 && input.length <= 500",
      "error_message": "Feedback must be 10-500 characters"
    }
  }
}
```

System automatically:
- Removes null bytes/control chars
- Rejects `<script>` tags, injection attempts
- HTML-escapes when displaying
- Validates length (your rule)

---

**Security Guarantees**:

The system guarantees:
- ✅ No null bytes in stored data
- ✅ No control characters (except newlines/tabs)
- ✅ No script tags or injection patterns
- ✅ All database queries parameterized
- ✅ All HTML output escaped
- ✅ Maximum input length enforced

**Your Responsibility**:
- Format validation (email, phone, date formats)
- Business rules (valid amounts, IDs, ranges)
- API backend validation

---

**Logging**:

Sanitization events logged for security monitoring:

```json
{
  "timestamp": "2024-11-29T10:30:45Z",
  "event": "input_rejected",
  "channel_user_id": "+254XXXXXX456",
  "bot_id": "550e8400-...",
  "reason": "suspicious_pattern_detected",
  "pattern_type": "script_tag"
}
```

Actual input content is NEVER logged (PII protection).

#### 2. API Credential Management

**Critical Rule**: Never put sensitive credentials directly in flow JSON files.

**❌ NEVER DO THIS**:

```json
{
  "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
      "Authorization": "Bearer sk_live_YOUR_SECRET_KEY_HERE" // ❌ EXPOSED!
    }
  }
}
```

**✅ RECOMMENDED APPROACH - Backend Proxy Pattern**:

Since the Bot Builder system does **NOT** have built-in credential injection:

1. **Deploy Your Own Backend API**: Create a backend service that your flows call
2. **Backend Handles Third-Party APIs**: Your backend manages all third-party API credentials
3. **Flows Call Your Backend**: API_ACTION nodes call your secure backend endpoints
4. **Your Backend Proxies Requests**: Your backend authenticates to third-party services

**Architecture**:

```
Bot Flow → API_ACTION → Your Backend (secure) → Third-Party API (with credentials)
                         ↓
                         (Credentials stored securely)
```

**Example Implementation**:

```json
// In your flow - calls YOUR backend
{
  "type": "API_ACTION",
  "config": {
    "request": {
      "method": "POST",
      "url": "https://your-backend.com/api/create-trip", // Your secure backend
      "body": {
        "user_id": "{{user.channel_id}}",
        "destination": "{{destination}}"
      }
    }
  }
}
```

```python
# Your backend service (example)
@app.post("/api/create-trip")
async def create_trip(request: TripRequest):
    # Your backend has the third-party API key
    api_key = os.getenv("THIRD_PARTY_API_KEY")

    # Your backend calls third-party API with credentials
    response = await third_party_api.create(
        headers={"Authorization": f"Bearer {api_key}"},
        data=request.dict()
    )

    return response
```

**Key Principles**:

- **Never put credentials in flow JSON**
- **Your backend is the security boundary**
- **Bot Builder flows are credential-free**
- **All authentication happens in your backend**

#### 3. PII (Personally Identifiable Information) Handling

**Data Collection Principles**:

- Collect only necessary information
- Inform users what data is being collected and why
- Store PII securely with encryption
- Implement data retention policies
- Provide mechanisms for data deletion upon request

**Sensitive Data Types**:

- Phone numbers (already collected as session key)
- Email addresses
- Full names
- Addresses
- Payment information
- Health information
- Government IDs

**Best Practices**:

```json
// ✅ GOOD - Clear purpose, validated format
{
  "type": "PROMPT",
  "config": {
    "text": "To process your order, please enter your email address:",
    "save_to_variable": "customer_email",
    "validation": {
      "type": "REGEX",
      "rule": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "error_message": "Please enter a valid email address"
    }
  }
}
```

#### 4. Template Injection Prevention

**Risk**: User input in templates could potentially expose sensitive data

**Safe Practices**:

- Never use unsanitized user input directly in templates
- User input is already stored in context variables (safe)
- Template engine only supports variable substitution (no code execution)
- No support for complex expressions reduces injection risk

**Example**:

```json
// ✅ SAFE - User input stored in variable, used in message
{
  "type": "TEXT",
  "config": {
    "text": "Hello {{user_name}}! Your request has been received."
  }
}
// Even if user_name contains "{{password}}", it displays literally
```

#### 5. Session Security

**Recommendations**:

- Implement session encryption at rest and in transit
- Use secure session tokens with proper authentication
- Implement rate limiting per user/session
- Monitor for suspicious patterns (multiple failed attempts, rapid requests)
- Regularly audit session data access
- Implement session timeout policies appropriately

#### 6. API Communication Security

**Requirements**:

- **Always use HTTPS** for API endpoints
- Validate SSL/TLS certificates
- Implement request signing for critical operations
- Use API rate limiting and throttling
- Log all API interactions for audit trails

**Example Secure API Configuration**:

```json
{
  "request": {
    "method": "POST",
    "url": "https://api.example.com/secure-endpoint", // ✅ HTTPS
    "headers": {
      "Content-Type": "application/json",
      "X-Request-ID": "{{request_id}}" // For tracing
    }
  }
}
```

#### 7. Error Message Security

**Avoid Exposing**:

- Internal system details
- Database structure or queries
- API endpoint details
- Stack traces
- User data from other sessions

**❌ INSECURE**:

```json
{
  "text": "Database connection failed: Connection refused to mysql://prod-db:3306/users"
}
```

**✅ SECURE**:

```json
{
  "text": "We're experiencing technical difficulties. Please try again later or contact support."
}
```

#### 8. Audit Logging

**What to Log**:

- User interactions (with timestamps)
- Flow state changes
- API calls made (without sensitive data in logs)
- Validation failures
- Session creation/termination
- Error occurrences

**What NOT to Log**:

- Plain-text passwords or secrets
- Full credit card numbers
- Raw PII without encryption
- API keys or tokens

**Example Log Entry**:

```json
{
  "timestamp": "2024-11-29T10:30:45Z",
  "channel": "whatsapp",
  "channel_user_id": "+254XXXXXX456", // Partially masked
  "bot_id": "550e8400-e29b-41d4-a716-446655440000",
  "flow_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "flow_name": "driver_onboarding",
  "node_id": "node_confirm_trip",
  "action": "user_input_received",
  "validation_result": "success"
}
```

### Security Checklist for Flow Developers

Before deploying a flow to production, verify:

- [ ] No API keys or secrets in flow JSON
- [ ] All API endpoints use HTTPS
- [ ] Input validation appropriate for data type (format, length, business rules)
- [ ] PII collected only when necessary
- [ ] Error messages don't expose system internals
- [ ] Rate limiting configured at infrastructure level
- [ ] Audit logging enabled
- [ ] Security review completed

**Note**: Input sanitization (null bytes, control chars, dangerous patterns) is automatic and requires no action from developers.

### Incident Response

**If a Security Breach Occurs**:

1. **Immediate Actions**:
   - Isolate affected systems
   - Disable compromised API keys immediately
   - Block suspicious sessions/phone numbers
2. **Assessment**:
   - Determine scope of breach
   - Identify compromised data
   - Document timeline
3. **Notification**:
   - Notify affected users (if PII exposed)
   - Report to regulatory authorities if required
   - Update security team
4. **Remediation**:
   - Patch vulnerabilities
   - Rotate all credentials
   - Update security measures
   - Conduct post-incident review

### Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)

---

## 11. What You CAN Do

### ✅ Conversation Patterns

1. **Sequential Data Collection**

   ```
   PROMPT (name) → PROMPT (email) → PROMPT (phone) → API_ACTION (save) → TEXT (confirm) → END
   ```

2. **Conditional Branching**

   ```
   API_ACTION (check user) → LOGIC_EXPRESSION → [existing user flow | new user flow]
   ```

3. **Dynamic Menus**

   ```
   API_ACTION (fetch items) → MENU (select item) → PROMPT (quantity) → API_ACTION (order)
   ```

4. **Retry with Validation**

   ```
   PROMPT (with validation) → [valid: next node | invalid: retry up to 3 times]
   ```

5. **Multi-Level Menus**

   ```
   MENU (category) → MENU (subcategory) → MENU (item) → PROMPT (confirm)
   ```

6. **API-Driven Logic**
   ```
   API_ACTION → LOGIC_EXPRESSION (check response) → [success path | error path]
   ```

### ✅ Use Cases

- **Forms**: Multi-step data collection with validation
- **Surveys**: Sequential questions with branching
- **Bookings**: Select date → time → location → confirm
- **E-commerce**: Browse → select → quantity → checkout
- **Support**: Issue type → details → ticket creation
- **Onboarding**: Registration → verification → setup

---

## 12. What You CANNOT Do

### ❌ Prohibited Patterns

1. **Parallel Processing**

   ```
   ❌ Cannot execute multiple API calls simultaneously
   ❌ Cannot process multiple nodes at once
   ❌ Cannot have concurrent user paths
   ```

2. **Loop Constructs**

   ```
   ❌ No for/while loops
   ❌ No iteration over arrays in nodes
   ✅ Cycles with input nodes allowed (PROMPT/MENU create natural breakpoints)
   ✅ Retry patterns supported via cycles back to input nodes
   ```

3. **Complex Computations**

   ```
   ❌ No arithmetic in templates: {{price * quantity}}
   ❌ No string manipulation: {{name.toUpperCase()}}
   ❌ No date calculations
   ❌ No aggregations (sum, average)
   ```

4. **External Dependencies**

   ```
   ❌ No file system access
   ❌ No database direct access (use API_ACTION)
   ❌ No WebSocket connections
   ❌ No scheduled tasks
   ❌ No push notifications
   ```

5. **Advanced Routing**

   ```
   ❌ No weighted random routing
   ❌ No time-based routing
   ❌ No A/B testing
   ❌ No user segmentation in routes
   ```

6. **State Management**
   ```
   ❌ No undo/redo functionality
   ❌ No session branching/forking
   ❌ No state snapshots
   ❌ No transaction rollback
   ```

### ❌ Anti-Patterns to Avoid

1. **Using PROMPT for Display**

   ```javascript
   // ❌ BAD
   "node_confirm": {
     "type": "PROMPT",
     "config": {
       "text": "Order confirmed!",
       "save_to_variable": "unused"
     }
   }

   // ✅ GOOD
   "node_confirm": {
     "type": "TEXT",
     "config": {
       "text": "Order confirmed!"
     }
   }
   ```

2. **Complex Validation in PROMPT**

   ```javascript
   // ❌ BAD - Do validation in API
   "validation": {
     "rule": "complex business logic here"
   }

   // ✅ GOOD - Simple validation in PROMPT, complex in API
   "validation": {
     "rule": "input.length >= 3"
   }
   // Then verify in API_ACTION node
   ```

3. **Deeply Nested Conditions**

   ```javascript
   // ❌ BAD
   "condition": "context.a && (context.b || context.c) && !context.d"

   // ✅ GOOD - Use separate LOGIC_EXPRESSION nodes
   ```

---

## 13. Best Practices

### 🎯 Flow Design

1. **Keep Nodes Focused**

   - One responsibility per node
   - Clear node names describing action
   - Short, focused messages

2. **Plan for Errors**

   - Always have error routes from API_ACTION
   - Provide retry options
   - Clear error messages
   - Graceful degradation

3. **Validate Early**

   - Validate in PROMPT nodes
   - Re-validate in API if needed
   - Clear error messages
   - Reasonable retry limits

4. **Use Appropriate Node Types**
   - PROMPT: Input collection only
   - MENU: Selection from options
   - TEXT: Information display
   - API_ACTION: External operations
   - LOGIC_EXPRESSION: Conditional routing

### 🎯 Context Management

1. **Initialize Variables**

   ```json
   "variables": {
     "user_name": { "type": "STRING", "default": null },
     "selected_items": { "type": "ARRAY", "default": [] }
   }
   ```

2. **Use Descriptive Names**

   - `driver_capacity` not `dc`
   - `from_location` not `from`
   - `selected_trip_id` not `sel_id`

3. **Clean Up Context**
   - Don't accumulate unnecessary data
   - Set to null when done
   - Be mindful of session size

### 🎯 Templating

1. **Initialize Variables with Defaults**

   Since the template engine doesn't support `||` for default values, initialize variables with defaults in your flow definition:

   ```json
   "variables": {
     "user_name": {"type": "string", "default": "Guest"},
     "items": {"type": "array", "default": []}
   }
   ```

   Then use in templates:

   ```
   Welcome, {{user_name}}!
   ```

2. **Keep Templates Simple**

   - Avoid deeply nested: `{{user.profile.settings.theme}}`
   - Extract to variable first if needed

3. **Test Edge Cases**
   - Null values
   - Empty arrays
   - Missing properties

### 🎯 API Integration

1. **Handle Timeouts**

   - Have error routes
   - Provide retry option
   - Don't leave user stuck

2. **Map Response Data**

   - Map only what you need
   - Use appropriate types
   - Handle missing fields

3. **Secure Credentials**
   - Never put API keys in flow
   - Use environment variables
   - Implement server-side auth

---

## Limitations Summary

### Technical Limitations

| Feature             | Limitation              | Workaround                |
| ------------------- | ----------------------- | ------------------------- |
| Auto-progression    | Max 10 steps            | Design shorter chains     |
| Validation attempts | Max 3 (default)         | Configure in defaults     |
| Session timeout     | 30 minutes              | User must restart         |
| Template complexity | Basic substitution only | Do complex logic in API   |
| Routing complexity  | Simple conditions only  | Break into multiple nodes |

### Design Limitations

| What You Want      | Why Not Possible           | Alternative                      |
| ------------------ | -------------------------- | -------------------------------- |
| For loops          | Not a programming language | Use cycles with PROMPT/MENU nodes |
| File uploads       | Not supported              | Use API with upload URL          |
| Real-time updates  | No push mechanism          | Poll with API_ACTION             |
| Scheduled messages | No scheduler               | Use external service + API       |
| A/B testing        | No built-in support        | Handle in API                    |

---

## Conclusion

The Bot Builder is designed for:

- ✅ Structured conversational flows
- ✅ Data collection and validation
- ✅ API integration
- ✅ Conditional branching
- ✅ User-driven navigation

It is NOT designed for:

- ❌ Complex computations
- ❌ Real-time features
- ❌ File handling
- ❌ Long-running processes
- ❌ Advanced programming constructs

**Golden Rule**: Keep flows simple, use APIs for complex logic, and design for the user experience first.
