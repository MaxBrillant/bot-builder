# SET_VARIABLE Node

Assigns values to flow variables, then auto-progresses to the next node.

## Overview

SET_VARIABLE nodes modify session context by setting one or more flow variables to configured values. They execute synchronously without user interaction or message display, immediately routing to the next node after assignments complete.

**Processor**: `backend/v1/app/processors/set_variable_processor.py`  
**Config Model**: `backend/v1/app/models/node_configs.py` (SetVariableNodeConfig, VariableAssignment)

### Key Characteristics

- **No user interaction**: Does not wait for input or display messages
- **Immediate progression**: Auto-routes after assignments complete
- **Template support**: Values support `{{variable}}` syntax with live rendering
- **Type conversion**: Converts rendered values to variable's declared type
- **Multiple assignments**: Can set 1-8 variables in a single node
- **Graceful fallback**: Template/conversion failures log warnings but don't crash session

## Configuration

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `type` | `"SET_VARIABLE"` | Yes | Literal | Node type discriminator |
| `assignments` | `VariableAssignment[]` | Yes | 1-8 items | Array of variable assignments to perform |

### VariableAssignment Structure

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `variable` | `string` | Yes | 1-96 chars, identifier pattern | Target variable name (must exist in flow variables) |
| `value` | `string` | Yes | 1-1024 chars | Value to assign (supports template syntax) |

**Variable Name Validation**:
- Must match identifier pattern: `^[a-zA-Z_][a-zA-Z0-9_]*$`
- Cannot be reserved keyword: `user`, `item`, `index`, `input`, `context`, `response`, `selection`, `true`, `false`, `null`, `success`, `error`, `_flow_variables`, `_flow_defaults`, `_api_result`
- Maximum length: 96 characters (enforced by `MAX_VARIABLE_NAME_LENGTH`)

**Value Constraints**:
- Maximum length: 1024 characters (enforced by `MAX_TEMPLATE_LENGTH`)
- Supports template syntax: `{{variable_name}}`
- Rendered at execution time using current session context

### Example Configuration

```json
{
  "id": "set_001",
  "name": "Initialize Checkout",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {
        "variable": "order_total",
        "value": "{{cart_subtotal}}"
      },
      {
        "variable": "discount_applied",
        "value": "false"
      },
      {
        "variable": "promo_code",
        "value": ""
      }
    ]
  },
  "routes": [
    {
      "condition": "always",
      "target_node": "prompt_002"
    }
  ],
  "position": {"x": 200, "y": 300}
}
```

## Behavior

### Execution Flow

1. **Retrieve flow variables**: Load `_flow_variables` from session context
2. **Process assignments** (in order):
   - **Template rendering**: Render `value` using `TemplateEngine.render_json_value()`
     - On failure: Log error, use unrendered value as fallback
   - **Type lookup**: Get variable's declared type from `_flow_variables`
   - **Type conversion**: Convert rendered value to target type using `ValidationSystem.convert_type()`
     - On failure: Log warning, store rendered string instead
   - **Context update**: Write converted value to `context[variable]`
   - **Logging**: Log each assignment at debug level
3. **Terminal check**: If node has no routes, return terminal result
4. **Route evaluation**: Evaluate routes using condition engine
5. **Return result**: ProcessResult with next_node and updated context (no message)

### Template Rendering

Values support template syntax for dynamic assignment:

```json
{
  "variable": "full_name",
  "value": "{{first_name}} {{last_name}}"
}
```

**Rendering Context**:
- Uses current session `context` (all stored variables)
- Uses `_flow_variables` type definitions for type-aware rendering
- Evaluates at execution time (not flow creation time)

**Type Preservation**:
- Simple variable templates (`{{variable}}` only) preserve native types (number, boolean, array) via `render_json_value()`
- Complex templates (`text {{var}} text`) fall back to string rendering regardless of variable type

**Error Handling**:
- Template parse errors → log error, use unrendered template string as fallback
- Missing variables → renders as literal template string (e.g., `{{missing}}` stays as-is)

### Type Conversion

After rendering, values are converted to the variable's declared type:

| Declared Type | Conversion Behavior | Example |
|---------------|---------------------|---------|
| `STRING` | Store as-is | `"hello"` → `"hello"` |
| `NUMBER` | Parse to int/float | `"42"` → `42`, `"3.14"` → `3.14` |
| `BOOLEAN` | Parse to bool | `"true"` → `true`, `"false"` → `false` |
| `ARRAY` | Parse JSON array | `"[1,2,3]"` → `[1, 2, 3]` |

**Conversion Failures**:
- Logs warning with variable name and target type
- Falls back to storing rendered string
- Session continues (does not crash)

**Example**: Setting `order_total` (type: NUMBER) to `"{{cart_subtotal}}"`:
- If `cart_subtotal` = `"49.99"` → converts to `49.99` (float)
- If `cart_subtotal` = `"invalid"` → logs warning, stores `"invalid"` (string)

### Auto-Progression

SET_VARIABLE nodes **never** wait for user input. After assignments complete:

1. If node has **no routes** → terminal result (session ends)
2. If node has **routes** → evaluate conditions and route immediately
3. If no route matches → raise `NoMatchingRouteError` (session terminates)

**Common Route Pattern**:
```json
"routes": [
  {
    "condition": "always",
    "target_node": "next_node"
  }
]
```

## Routes

### Route Evaluation

Routes are evaluated using the standard condition engine after assignments complete. All assigned variables are available in routing conditions.

**Available Variables in Conditions**:
- All session context variables (including just-assigned values)
- Standard context properties: `input`, `selection`, `response`, etc.

**Common Patterns**:

| Pattern | Condition | Use Case |
|---------|-----------|----------|
| Unconditional | `"always"` | Standard progression (most common) |
| Conditional | `"order_total > 100"` | Branch based on assigned value |
| Multiple conditions | `"discount_applied == true"` | Complex logic after assignment |

### Example: Conditional Routing

```json
{
  "assignments": [
    {
      "variable": "order_total",
      "value": "{{cart_subtotal}}"
    }
  ],
  "routes": [
    {
      "condition": "order_total > 100",
      "target_node": "show_discount"
    },
    {
      "condition": "order_total <= 100",
      "target_node": "show_checkout"
    }
  ]
}
```

### Terminal Nodes

If `routes` is `null` or empty array, node is **terminal**:
- Returns `ProcessResult(next_node=None)`
- Session ends after assignments complete
- No error raised (intentional flow termination)

## Constraints

### System Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max assignments per node | 8 | `MAX_ASSIGNMENTS_PER_SET_VARIABLE` |
| Max variable name length | 96 chars | `MAX_VARIABLE_NAME_LENGTH` |
| Max value length | 1024 chars | `MAX_TEMPLATE_LENGTH` |
| Max routes per node | 8 | `MAX_ROUTES_PER_NODE` |

**Source**: `backend/v1/app/utils/constants/constraints.py`

### Validation Rules

**At Flow Creation Time** (Pydantic validation):
- Assignments array must have 1-8 items
- Variable names must match identifier pattern
- Variable names cannot be reserved keywords
- Values must be 1-1024 characters

**At Runtime** (processor validation):
- Variable must exist in `_flow_variables` (checked via `_get_variable_type()`)
- If variable not found, logs warning and uses STRING type as default

### Reserved Keywords

These variable names **cannot** be used in assignments:
- `user` — reserved for user metadata
- `item` — reserved for dynamic menu items
- `index` — reserved for dynamic menu indexing
- `input` — reserved for user input in PROMPT/MENU nodes
- `context` — reserved for session context
- `response` — reserved for API_ACTION response data
- `selection` — reserved for menu selection index
- `true` — reserved boolean literal
- `false` — reserved boolean literal
- `null` — reserved null literal
- `success` — reserved for API_ACTION success flag
- `error` — reserved for API_ACTION error flag
- `_flow_variables` — internal flow variable metadata
- `_flow_defaults` — internal flow defaults
- `_api_result` — internal API result flag

**Source**: `backend/v1/app/utils/constants/patterns.py` (RESERVED_KEYWORDS)

### Error Conditions

| Error | Trigger | Behavior |
|-------|---------|----------|
| Template rendering fails | Invalid template syntax | Log error, use unrendered value |
| Type conversion fails | Value incompatible with type | Log warning, store as string |
| Variable not found | Variable not in `_flow_variables` | Log warning, use STRING type |
| No matching route | All route conditions false | Raise `NoMatchingRouteError`, terminate session |
| Terminal node | No routes defined | Return `next_node=None`, end session |

**Graceful Degradation**: Template and conversion errors do NOT crash the session. The processor logs warnings and continues with fallback values.

## Examples

### Example 1: Simple Initialization

Initialize multiple variables to default values:

```json
{
  "id": "set_init",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {"variable": "step", "value": "1"},
      {"variable": "completed", "value": "false"},
      {"variable": "error_count", "value": "0"}
    ]
  },
  "routes": [
    {"condition": "always", "target_node": "welcome_text"}
  ]
}
```

**Execution**:
- Sets `step` = `1` (NUMBER)
- Sets `completed` = `false` (BOOLEAN)
- Sets `error_count` = `0` (NUMBER)
- Routes to `welcome_text`

### Example 2: Template-Based Assignment

Calculate derived values using templates:

```json
{
  "id": "set_totals",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {
        "variable": "full_name",
        "value": "{{first_name}} {{last_name}}"
      },
      {
        "variable": "order_summary",
        "value": "Order #{{order_id}} - Total: ${{cart_total}}"
      }
    ]
  },
  "routes": [
    {"condition": "always", "target_node": "show_confirmation"}
  ]
}
```

**Context Before**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "order_id": "12345",
  "cart_total": "49.99"
}
```

**Context After**:
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "order_id": "12345",
  "cart_total": "49.99",
  "full_name": "John Doe",
  "order_summary": "Order #12345 - Total: $49.99"
}
```

### Example 3: Conditional Routing After Assignment

Set a flag and route based on its value:

```json
{
  "id": "set_discount",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {
        "variable": "discount_amount",
        "value": "{{order_total}} * 0.1"
      },
      {
        "variable": "discount_applied",
        "value": "true"
      }
    ]
  },
  "routes": [
    {
      "condition": "discount_amount > 10",
      "target_node": "show_big_discount"
    },
    {
      "condition": "discount_amount <= 10",
      "target_node": "show_small_discount"
    }
  ]
}
```

**Note**: This assumes `order_total * 0.1` is pre-calculated. Template engine does NOT evaluate math expressions—use LOGIC_EXPRESSION nodes for calculations.

### Example 4: Reset Flow State

Clear variables at the start of a retry loop:

```json
{
  "id": "set_reset",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {"variable": "user_input", "value": ""},
      {"variable": "validation_error", "value": ""},
      {"variable": "retry_count", "value": "0"}
    ]
  },
  "routes": [
    {"condition": "always", "target_node": "prompt_start"}
  ]
}
```

### Example 5: API Response Processing

Store API response data in variables for later use:

```json
{
  "id": "set_user_data",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {
        "variable": "user_status",
        "value": "{{api_user_status}}"
      },
      {
        "variable": "account_balance",
        "value": "{{api_balance}}"
      }
    ]
  },
  "routes": [
    {
      "condition": "user_status == 'active'",
      "target_node": "show_account"
    },
    {
      "condition": "user_status != 'active'",
      "target_node": "show_suspended"
    }
  ]
}
```

**Flow**: API_ACTION → SET_VARIABLE → Conditional routing based on API data

### Example 6: Terminal Node (No Routes)

Set final state before ending session:

```json
{
  "id": "set_final",
  "type": "SET_VARIABLE",
  "config": {
    "type": "SET_VARIABLE",
    "assignments": [
      {"variable": "session_ended", "value": "true"},
      {"variable": "end_time", "value": "{{current_timestamp}}"}
    ]
  },
  "routes": null
}
```

**Behavior**: After assignments complete, session terminates gracefully (no error).
