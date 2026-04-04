# Node System Overview

Shared structures and behaviors across all node types in the Bot Builder conversation flow system.

## Overview

Nodes are the building blocks of conversation flows. All 6 node types share a common base structure defined in `app/models/node_configs.py`, with type-specific configuration isolated in discriminated unions. The `app/processors/base_processor.py` provides shared processing logic, while `app/processors/factory.py` handles instantiation.

## Node Types

| Type | Needs Input | Purpose | Doc |
|------|-------------|---------|-----|
| PROMPT | Yes | Ask question, validate input, store to variable | [prompt.md](prompt.md) |
| MENU | Yes | Display options (static or dynamic), handle selection | [menu.md](menu.md) |
| API_ACTION | No | Make HTTP request, map response to variables | [api-action.md](api-action.md) |
| LOGIC_EXPRESSION | No | Conditional branching based on context | [logic.md](logic.md) |
| TEXT | No | Send message without waiting for input | [text.md](text.md) |
| SET_VARIABLE | No | Assign values to flow variables | [set-variable.md](set-variable.md) |

## Base Node Structure

Every node is a `FlowNode` instance with these fields:

| Field | Type | Max Length | Required | Description |
|-------|------|------------|----------|-------------|
| id | string | 96 chars | Yes | Unique identifier within flow |
| name | string | 50 chars | Yes | Human-readable name |
| type | enum | - | Yes | One of 6 node types above |
| config | NodeConfig | - | Yes | Type-specific configuration (discriminated union) |
| routes | Route[] | 8 routes | No | Routing rules (omit for terminal nodes) |
| position | {x, y} | - | Yes | Canvas coordinates |

Defined in `app/models/node_configs.py` lines 910-999.

## Routes

Routes define transitions between nodes. Evaluated in order, first match wins.

| Field | Type | Max Length | Description |
|-------|------|------------|-------------|
| condition | string | 512 chars | Expression to evaluate (e.g., "success", "selection == 1") |
| target_node | string | 96 chars | Node ID to transition to when condition true |

**Evaluation:**
- Routes evaluated by `BaseProcessor.evaluate_routes()` (lines 106-159)
- Already sorted by engine before reaching processor (specific conditions first, "true" last)
- Uses `ConditionEvaluator` to evaluate expressions against context
- Returns target node ID of first match, or None if no match
- Empty routes array = terminal node (conversation ends)

Defined in `app/models/node_configs.py` lines 634-653.

## ProcessResult

Return type for all node processors. Communicates execution outcome to engine.

| Field | Type | Description |
|-------|------|-------------|
| message | string? | Optional message to send to user |
| needs_input | bool | True if processor needs user input (wait state) |
| next_node | string? | ID of next node to execute (None if needs input or terminal) |
| context | dict | Updated context dictionary |
| terminal | bool | True if this node terminates conversation |
| status | string? | Optional status indicator (e.g., 'COMPLETED', 'ERROR') |

**Usage patterns:**
- Input nodes (PROMPT, MENU): `needs_input=True` on first call, then `next_node=X` after receiving input
- Non-input nodes: `next_node=X` immediately
- Terminal nodes: `next_node=None` with no routes — engine detects terminal via `check_terminal()` or when node has no routes and `next_node` is None
- Error states: Processors can either raise exceptions OR return `status="ERROR"` in ProcessResult (engine checks both patterns)

Defined in `app/processors/base_processor.py` lines 19-37.

## Auto-progression

Non-input nodes (TEXT, API_ACTION, LOGIC_EXPRESSION, SET_VARIABLE) auto-progress without user input.

**Hard limit:** 10 consecutive non-input nodes (`SystemConstraints.MAX_AUTO_PROGRESSION`)

**Tracking:**
- Incremented in `FlowExecutor.execute()` loop (`app/core/engine.py` lines 453-459, 590-599)
- Reset to 0 when node needs input (line 554)
- Tracked in session (`session.auto_progression_count`)
- Checked before and after each node execution
- Exceeding limit raises `MaxAutoProgressionError` and terminates session

**Why it exists:**
- Prevents infinite loops in flow logic
- Protects against misconfigured flows with circular LOGIC_EXPRESSION chains
- Ensures flows eventually require user input

## Shared Components

### Interrupt

Allows user to exit current flow by entering specific keywords. Used by PROMPT and MENU nodes.

| Field | Type | Max Length | Validation |
|-------|------|------------|------------|
| input | string | 96 chars | Cannot be empty or whitespace-only |
| target_node | string | 96 chars | Must reference valid node ID |

**Behavior:**
- Checked before validation in PROMPT/MENU processors
- Case-insensitive matching
- Whitespace trimmed before comparison
- Exact match required after trim/lowercase
- Whitespace within keyword allowed ("go back", "cancel order")

Defined in `app/models/node_configs.py` lines 262-304.

### ValidationRule

Validation for PROMPT nodes. Supports regex or expression-based validation.

| Field | Type | Max Length | Description |
|-------|------|------------|-------------|
| type | "REGEX" \| "EXPRESSION" | - | Validation method |
| rule | string | 512 chars | Regex pattern or expression |
| error_message | string | 512 chars | Message shown when validation fails |

**REGEX validation:**
- Standard regex syntax with restrictions
- No lookahead/lookbehind assertions (`(?=`, `(?!`, `(?<=`, `(?<!`)
- No named groups (`(?P<name>...`)
- Pattern must compile with Python `re` module

**EXPRESSION validation:**
- Supported methods: `input.isAlpha()`, `input.isNumeric()`, `input.isDigit()`
- Supported property: `input.length`
- Comparison operators: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Logical operators: `&&`, `||`
- Context variable access: `context.variable_name`
- Unsupported: `parseInt()`, `toUpperCase()`, `includes()`, custom functions

Defined in `app/models/node_configs.py` lines 105-260.

### Variable Assignment

Used by SET_VARIABLE nodes. Assigns values to flow variables with template support.

| Field | Type | Max Length | Description |
|-------|------|------------|-------------|
| variable | string | 96 chars | Variable name (identifier pattern, not reserved) |
| value | string | 1024 chars | Value to assign (supports template variables) |

Defined in `app/models/node_configs.py` lines 841-872.

## BaseProcessor

Abstract base class for all node processors. Shared functionality:

**Methods:**
- `process()` — Abstract method implemented by each processor
- `evaluate_routes()` — Evaluate routes in order, return first match
- `check_interrupt()` — Check if input matches interrupt keyword
- `check_terminal()` — Check if node has no routes, return terminal result
- `raise_no_matching_route()` — Raise NoMatchingRouteError
- `get_nested_value()` — Traverse objects using dot notation
- `sanitize_input()` — Trim whitespace from user input
- `_get_node_type_display()` — Get display name for logging (LOGIC_EXPRESSION → LOGIC)
- `_get_variable_type()` — Get variable type from context

**Dependencies injected via constructor:**
- `template_engine` — TemplateEngine instance for variable substitution
- `condition_evaluator` — ConditionEvaluator for route conditions
- `validation_system` — InputValidator for PROMPT validation
- `session_manager` — SessionManager for retry tracking (optional)

Defined in `app/processors/base_processor.py` lines 40-357.

## ProcessorFactory

Creates processor instances with dependency injection. Eliminates hardcoded instantiation from engine.

**Registry:**
- PROMPT → PromptProcessor
- MENU → MenuProcessor
- API_ACTION → APIActionProcessor
- LOGIC_EXPRESSION → LogicProcessor
- TEXT → TextProcessor
- SET_VARIABLE → SetVariableProcessor

**Features:**
- Lazy instantiation (processors created on first use)
- Singleton pattern (one instance per node type per factory)
- Extensible registration system via `register()` method
- Handles special dependencies (APIActionProcessor requires `http_client`)

**Usage:**
```python
factory = ProcessorFactory(
    template_engine=template_engine,
    condition_evaluator=evaluator,
    validation_system=validator,
    http_client=client,
    session_manager=manager
)

processor = factory.create(NodeType.PROMPT.value)
result = await processor.process(node, context, user_input, session, db)
```

Defined in `app/processors/factory.py` lines 27-214.

## Constraints

| Constraint | Value | Applies To | Enforced By |
|------------|-------|------------|-------------|
| MAX_AUTO_PROGRESSION | 10 | Consecutive non-input nodes | FlowExecutor (engine.py) |
| MAX_NODES_PER_FLOW | 48 | Nodes in flow | Flow validation (API layer) |
| MAX_ROUTES_PER_NODE | 8 | Routes per node | FlowNode field validator |
| MAX_NODE_ID_LENGTH | 96 chars | Node IDs | FlowNode field validator |
| MAX_MESSAGE_LENGTH | 1024 chars | Text/prompt messages | Node config validators |
| MAX_ROUTE_CONDITION_LENGTH | 512 chars | Route conditions | Route field validator |
| MAX_INTERRUPT_KEYWORD_LENGTH | 96 chars | Interrupt keywords | Interrupt field validator |
| MAX_ERROR_MESSAGE_LENGTH | 512 chars | Validation error messages | ValidationRule field validator |
| MAX_VARIABLE_NAME_LENGTH | 96 chars | Variable names | Various field validators |
| MAX_TEMPLATE_LENGTH | 1024 chars | Template strings | Various field validators |

Full list in `app/utils/constants/constraints.py`.

## Node Processing Flow

1. **Engine calls processor** — `FlowExecutor.execute()` gets processor from factory
2. **Processor executes** — `processor.process(node, context, user_input, session, db)`
3. **Input nodes wait** — Return `ProcessResult(needs_input=True)` on first call
4. **Engine waits** — Session persisted, user input awaited
5. **User responds** — Webhook delivers input, engine resumes session
6. **Processor continues** — Called again with user input, validates, evaluates routes
7. **Return next node** — `ProcessResult(next_node="node_xyz", context=updated_context)`
8. **Auto-progression** — Engine loops through non-input nodes until input needed or terminal
9. **Terminal or error** — Session ends when `next_node=None` or exception raised

## Code Paths

| Component | Path |
|-----------|------|
| Node models | `app/models/node_configs.py` |
| Base processor | `app/processors/base_processor.py` |
| Factory | `app/processors/factory.py` |
| Node processors | `app/processors/{type}_processor.py` |
| Engine (orchestration) | `app/core/engine.py` |
| Constants | `app/utils/constants/constraints.py` |
| Enums | `app/utils/constants/enums.py` |
