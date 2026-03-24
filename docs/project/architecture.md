# Backend Architecture

## Three-Tier Hierarchy

```
User (1) → (N) Bots → (N) Flows
```

- **User**: Authenticated account holder
- **Bot**: Logical grouping of flows with unique webhook URL
- **Flow**: Conversation definition with nodes and routing logic

## Platform-Agnostic Design

The core system is messaging-platform-agnostic. Integration layers (WhatsApp via Evolution API, etc.) translate platform-specific messages to a normalized format and POST to bot webhooks: `/webhook/{bot_id}`

Sessions are keyed by: `channel:channel_user_id:bot_id`

## Flow Processing

`ConversationOrchestrator` in `engine.py` drives execution:

1. Receive message via webhook
2. Load or create session for `channel:user:bot`
3. Match trigger keyword (bot-scoped) to select flow
4. Process current node via appropriate processor
5. Evaluate routes (sorted by specificity) to determine next node
6. Auto-progress through non-input nodes (max 10)
7. Return response to integration layer

## Node Types and Processors

Each node type has a dedicated processor in `app/processors/` inheriting from `BaseProcessor`:

| Node Type | Processor | Behavior |
|-----------|-----------|---------|
| `PROMPT` | `PromptProcessor` | Collect user input with validation |
| `MENU` | `MenuProcessor` | Display options (static or dynamic) |
| `API_ACTION` | `APIActionProcessor` | Call external API, store response |
| `LOGIC_EXPRESSION` | `LogicProcessor` | Conditional routing only, no output |
| `TEXT` | `TextProcessor` | Display text, auto-progress |
| `SET_VARIABLE` | `SetVariableProcessor` | Set variable, auto-progress |

Processors return `ProcessResult`:
- `message`: Response text (template-rendered)
- `needs_input`: Whether to wait for user response
- `next_node`: Next node ID or None
- `context`: Updated session variables
- `terminal`: Whether conversation ends

## Template System

Variables use `{{variable_name}}` syntax against a flat context dict.

**Works:**
- `{{variable_name}}` — any flow variable
- `{{nested.field}}` — dot notation (e.g. `{{user.channel_id}}` in API_ACTION, `{{item.name}}` in MENU item_template)
- `{{items.0}}` — array index

**Does NOT work:**
- `{{context.variable_name}}` — no `context` key exists; renders literally
- `{{session.channel_user_id}}` — not implemented
- `{{api.field_name}}` — not implemented; use `response_map` to store API values

**Special variables (location-restricted):**
- `{{user.channel_id}}`, `{{user.channel}}` — API_ACTION nodes only
- `{{item.*}}`, `{{index}}` — MENU `item_template` only
- `{{current_attempt}}`, `{{max_attempts}}` — retry_logic `counter_text` only

## Route Evaluation

Routes evaluated in sorted order (specific before catch-all):
1. Sort via `sort_routes()` in `conditions.py`
2. Evaluate with `ConditionEvaluator`
3. First match wins

Condition syntax:
- `context.age > 18`
- `input.contains("yes")`
- `context.verified && input == "1"`

## Session Management

- 30-minute absolute timeout (not sliding)
- State persisted in PostgreSQL
- Redis required for rate limiting and token blacklisting
- Auto-cleanup every 10 minutes via background task

## System Constraints

| Constraint | Limit | Reason |
|------------|-------|--------|
| Max nodes per flow | 48 | Performance |
| Max routes per node | 8 | Complexity |
| Session timeout | 30 min | Resource management |
| API timeout | 30 seconds | Fixed |
| Max auto-progression | 10 nodes | Prevent infinite loops |

## Adding a New Node Type

1. Define config model in `app/models/node_configs.py`
2. Create processor in `app/processors/[type]_processor.py`
3. Register in `ProcessorFactory` (`app/processors/factory.py`)
4. Add to `NodeType` enum in `app/utils/constants.py`
