# Route Sorting

## Overview

The route sorting system ensures routes are evaluated in the correct priority order during conversation flow execution. Routes with more specific conditions are evaluated before catch-all routes to prevent premature matches.

**Implementation**: `backend/v1/app/core/conditions.py` (RouteSorter class, lines 242-335)

**Frontend Mirror**: The backend sorting logic mirrors `routeConditionUtils.ts` on the frontend for consistency.

## Why Order Matters

Routes are evaluated sequentially using first-match semantics. If a catch-all route appears before specific routes, the specific routes will never be evaluated:

```python
# WRONG ORDER - catch-all evaluated first, specific routes unreachable
routes = [
    {"condition": "true", "target_node": "node_x"},           # Matches everything
    {"condition": "selection == 1", "target_node": "node_a"}, # Never reached
    {"condition": "selection == 2", "target_node": "node_b"}  # Never reached
]

# CORRECT ORDER - specific routes evaluated first
routes = [
    {"condition": "selection == 1", "target_node": "node_a"}, # Checked first
    {"condition": "selection == 2", "target_node": "node_b"}, # Checked second
    {"condition": "true", "target_node": "node_x"}            # Fallback checked last
]
```

## Sorting Algorithm

```python
RouteSorter.sort_routes(routes: List[Dict], node_type: str) -> List[Dict]
```

1. Creates shallow copy of routes list (never mutates original)
2. Computes priority score for each route based on condition + node_type
3. Sorts by priority score (ascending - lower number = evaluated first)
4. Returns sorted copy

**Stability**: Python's `sort()` is stable - routes with equal priority maintain their original relative order.

## Priority Rules

Priority is computed by `get_condition_priority(condition: str, node_type: str) -> int`.

Lower priority number = evaluated first (higher precedence).

| Priority | Condition Type | Node Types | Notes |
|----------|----------------|------------|-------|
| 1 | `success` | API_ACTION | Success path evaluated before error path |
| 2 | `error` | API_ACTION | Error path evaluated second |
| N | `selection == N` | MENU (static only) | Selection 1 before 2 before 3, etc. |
| 500 | Custom expressions | LOGIC_EXPRESSION | Maintains definition order (stable sort) |
| 500 | Other conditions | All | Default priority for unrecognized patterns |
| 1000 | `true` | LOGIC_EXPRESSION, PROMPT, TEXT, SET_VARIABLE, DYNAMIC_MENU | Catch-all always evaluated last |

## Per-Node-Type Behavior

| Node Type | Valid Conditions | Sorting Behavior |
|-----------|------------------|------------------|
| **MENU** (static) | `selection == 1`, `selection == 2`, ... | Numeric extraction from condition string. Routes sorted by selection number. |
| **API_ACTION** | `success`, `error` | Hardcoded: success=1, error=2. Success path always evaluated first. |
| **LOGIC_EXPRESSION** | Custom expressions, `true` | Custom expressions get priority 500 (maintain order). `true` gets 1000 (evaluated last). |
| **PROMPT** | `true` | Single route with `true` condition (priority 1000). |
| **TEXT** | `true` | Single route with `true` condition (priority 1000). |
| **SET_VARIABLE** | `true` | Single route with `true` condition (priority 1000). |
| **DYNAMIC_MENU** | `true` | Only `true` condition allowed (priority 1000). Selection conditions not supported. |

## Priority Assignment Examples

```python
# MENU node
get_condition_priority("selection == 1", "MENU")     # Returns: 1
get_condition_priority("selection == 2", "MENU")     # Returns: 2
get_condition_priority("selection == 10", "MENU")    # Returns: 10
get_condition_priority("true", "MENU")               # Returns: 1000

# API_ACTION node
get_condition_priority("success", "API_ACTION")      # Returns: 1
get_condition_priority("error", "API_ACTION")        # Returns: 2

# LOGIC_EXPRESSION node
get_condition_priority("context.age > 18", "LOGIC_EXPRESSION")    # Returns: 500
get_condition_priority("context.status == 'active'", "LOGIC_EXPRESSION") # Returns: 500
get_condition_priority("true", "LOGIC_EXPRESSION")                # Returns: 1000

# Nodes with single route
get_condition_priority("true", "PROMPT")             # Returns: 1000
get_condition_priority("true", "TEXT")               # Returns: 1000
get_condition_priority("true", "SET_VARIABLE")       # Returns: 1000
```

## MENU Selection Extraction

For MENU nodes, priority is extracted from the condition string using regex:

```python
pattern = r'selection\s*==\s*(\d+)'

# Matches:
"selection == 1"      # Extracts: 1
"selection==2"        # Extracts: 2
"selection  ==  10"   # Extracts: 10

# No match → returns default priority 500:
"invalid_condition"
"selection > 1"
"context.x == 1"
```

## Catch-All Routes

The `true` condition acts as a catch-all (matches any context):

- **Valid on**: LOGIC_EXPRESSION, PROMPT, TEXT, SET_VARIABLE, DYNAMIC_MENU (DYNAMIC_MENU only allows `true`, no selection conditions)
- **Invalid on**: API_ACTION (only `success`/`error` allowed), MENU (only `selection == N` allowed)
- **Priority**: Always 1000 (evaluated last)
- **Case-insensitive**: `true`, `True`, `TRUE` all treated identically

## Immutability

```python
original_routes = [
    {"condition": "true", "target_node": "fallback"},
    {"condition": "selection == 1", "target_node": "option1"}
]

sorted_routes = RouteSorter.sort_routes(original_routes, "MENU")

# original_routes is unchanged (still has "true" first)
# sorted_routes is new list with correct order (selection first, true last)
```

The `sort_routes()` method creates a shallow copy before sorting, ensuring the original routes list is never mutated.

## Integration Points

Routes are sorted in processors before evaluation:

```python
# Example from processors/menu_processor.py
routes = node_config.routes
sorted_routes = RouteSorter.sort_routes(routes, "MENU")

for route in sorted_routes:
    if self.evaluator.evaluate(route['condition'], context):
        return route['target_node']
```

All processors that handle multi-route nodes (MENU, API_ACTION, LOGIC_EXPRESSION, DYNAMIC_MENU) invoke `RouteSorter.sort_routes()` before iterating routes.

## Logging

Sorting operations emit debug-level logs:

```
Sorted {count} routes for {node_type}
  node_type: MENU
  route_count: 3
  conditions: ["selection == 1", "selection == 2", "true"]
```

## Backward Compatibility

A standalone function wrapper exists for legacy code:

```python
def sort_routes(routes: List[Dict], node_type: str) -> List[Dict]:
    return RouteSorter.sort_routes(routes, node_type)
```

New code should use `RouteSorter.sort_routes()` directly.

## Constraints

- **Priority range**: 1-1000 (lower = higher precedence)
- **Selection range**: MENU conditions support `selection == N` where N is any positive integer
- **No side effects**: Original routes list never modified
- **Stable sort**: Routes with equal priority maintain relative order
- **Type safety**: Condition and node_type must be strings; routes must be list of dicts
- **Pattern matching**: MENU selection extraction requires exact `selection == N` format (single space around `==`, enforced by validation regex `^selection == \d+$`)
- **Case sensitivity**: Catch-all matching is case-insensitive (`true` == `True` == `TRUE`), but other conditions are case-sensitive
