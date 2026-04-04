# LOGIC_EXPRESSION Node

Internal conditional routing without user interaction.

## Overview

LOGIC_EXPRESSION nodes evaluate conditions against session context to route conversations to the appropriate next node. They execute immediately without displaying messages or waiting for user input.

**Key characteristics:**
- Auto-progresses (no user interaction)
- No message display
- Evaluates route conditions using `app.core.conditions` evaluator
- Routes based on context variables and expressions

**Common use cases:**
- Branch based on API response data
- Check if arrays are empty
- Route by user type or status
- Implement if-else logic

## Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"LOGIC_EXPRESSION"` | Yes | Node type identifier |

**Configuration model:** `LogicExpressionNodeConfig` (line 829-838, `app/models/node_configs.py`)

The config object is empty — all routing logic is defined in the node's `routes` array.

## Behavior

**Processor:** `LogicProcessor` (`app/processors/logic_processor.py`)

**Processing flow:**

1. **Terminal check** — calls `BaseProcessor.check_terminal()` to verify node has routes
   - If no routes exist, returns terminal result (session ends)
   
2. **Route evaluation** — calls `BaseProcessor.evaluate_routes()` with current context
   - Iterates through `node.routes` in order
   - First route with truthy condition wins
   
3. **No matching route** — calls `BaseProcessor.raise_no_matching_route()` if no condition matches
   - Raises `NoMatchingRouteError`
   - Session ends with error

4. **Return result** — returns `ProcessResult` with `next_node` and `context`
   - No message
   - Immediate progression to next node

**Key method:** `LogicProcessor.process()` (lines 32-76)

## Routes

Routes are **required** for LOGIC_EXPRESSION nodes. Each route contains:

| Field | Type | Description |
|-------|------|-------------|
| `condition` | `str` | Expression to evaluate (1-512 chars) |
| `target_node` | `str` | Node ID to route to when condition is true |

**Evaluation order:** Top to bottom, first match wins.

**Example route conditions:**
```json
[
  {"condition": "user_type == \"premium\"", "target_node": "premium_flow"},
  {"condition": "cart_items.length > 0", "target_node": "checkout"},
  {"condition": "api_status == \"error\"", "target_node": "error_handler"},
  {"condition": "true", "target_node": "default_fallback"}
]
```

**Expression syntax:** See condition evaluator in `app/core/conditions.py` for supported operators and functions.

## Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max routes per node | 8 | `SystemConstraints.MAX_ROUTES_PER_NODE` |
| Max condition length | 512 chars | `SystemConstraints.MAX_ROUTE_CONDITION_LENGTH` |
| Max node ID length | 96 chars | `SystemConstraints.MAX_NODE_ID_LENGTH` |
| Auto-progression limit | 10 consecutive non-input nodes | System-wide limit (prevents infinite loops) |

**Terminal nodes:** LOGIC_EXPRESSION nodes without routes are terminal and end the session.

**Error handling:**
- `NoMatchingRouteError` — raised when no route condition evaluates to true
- Session ends immediately when error is raised

## Examples

### Basic branching

```json
{
  "id": "check_payment_status",
  "name": "Check Payment",
  "type": "LOGIC_EXPRESSION",
  "config": {
    "type": "LOGIC_EXPRESSION"
  },
  "routes": [
    {
      "condition": "payment_status == \"success\"",
      "target_node": "order_confirmation"
    },
    {
      "condition": "payment_status == \"pending\"",
      "target_node": "pending_notice"
    },
    {
      "condition": "true",
      "target_node": "payment_failed"
    }
  ]
}
```

### Check array emptiness

```json
{
  "id": "check_cart",
  "name": "Validate Cart",
  "type": "LOGIC_EXPRESSION",
  "config": {
    "type": "LOGIC_EXPRESSION"
  },
  "routes": [
    {
      "condition": "cart_items.length > 0",
      "target_node": "show_cart"
    },
    {
      "condition": "true",
      "target_node": "empty_cart_message"
    }
  ]
}
```

### Multi-condition logic

```json
{
  "id": "eligibility_check",
  "name": "Check Eligibility",
  "type": "LOGIC_EXPRESSION",
  "config": {
    "type": "LOGIC_EXPRESSION"
  },
  "routes": [
    {
      "condition": "user_age >= 18 && account_verified == true",
      "target_node": "full_access"
    },
    {
      "condition": "user_age >= 18",
      "target_node": "verify_account_prompt"
    },
    {
      "condition": "true",
      "target_node": "age_restricted"
    }
  ]
}
```

### API response routing

```json
{
  "id": "api_result_router",
  "name": "Route API Result",
  "type": "LOGIC_EXPRESSION",
  "config": {
    "type": "LOGIC_EXPRESSION"
  },
  "routes": [
    {
      "condition": "api_results.length == 0",
      "target_node": "no_results_found"
    },
    {
      "condition": "api_results.length == 1",
      "target_node": "single_result_display"
    },
    {
      "condition": "true",
      "target_node": "multiple_results_menu"
    }
  ]
}
```
