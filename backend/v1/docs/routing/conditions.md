# Route Conditions

Comprehensive documentation of the route condition system based on source code analysis.

**Source files:**
- `backend/v1/app/core/conditions.py` - ConditionEvaluator class
- `backend/v1/app/models/node_configs.py` - Route model
- `backend/v1/app/core/flow_validator.py` - RouteConditionValidator class

---

## Overview

Routes control flow execution by evaluating conditions against session context. Each route has a condition expression that determines whether the route should be taken. When a node completes processing, the engine evaluates routes in order until a condition matches.

The condition system supports:
- Special keywords for node-specific routing (`success`, `error`, `true`)
- Comparison expressions with operators
- Logical operators for compound conditions
- Context variable access via `context.*` notation
- Type-safe evaluation with no automatic coercion
- Direct variable references (without `context.` prefix)

---

## Condition Keywords

Keywords provide node-specific routing behavior without requiring expressions.

| Keyword | Nodes | Meaning | Context Check |
|---------|-------|---------|---------------|
| `true` | PROMPT, TEXT, LOGIC_EXPRESSION, SET_VARIABLE, DYNAMIC MENU | Always matches (catch-all) | Returns `True` |
| `success` | API_ACTION | API call succeeded | `context.get('_api_result') == 'success'` |
| `error` | API_ACTION | API call failed | `context.get('_api_result') == 'error'` |
| `selection == N` | STATIC MENU | User selected option N (1-indexed) | Special pattern validation |

**Examples:**
```json
{"condition": "true", "target_node": "next_node"}
{"condition": "success", "target_node": "process_result"}
{"condition": "error", "target_node": "handle_failure"}
{"condition": "selection == 1", "target_node": "option_1_flow"}
```

**Validation:** Keywords are validated per node type. Using `success`/`error` on non-API_ACTION nodes fails validation. Using `selection == N` on non-STATIC MENU nodes fails validation.

---

## Comparison Operators

Operators compare values with strict type checking. No automatic type coercion occurs.

| Operator | Description | Type Requirements | Booleans Excluded |
|----------|-------------|-------------------|-------------------|
| `==` | Equality | Any types, no coercion | No |
| `!=` | Inequality | Any types, no coercion | No |
| `>` | Greater than | Both must be int/float | Yes |
| `<` | Less than | Both must be int/float | Yes |
| `>=` | Greater or equal | Both must be int/float | Yes |
| `<=` | Less or equal | Both must be int/float | Yes |

**Type Coercion:** None. Comparing string `"10"` to number `5` returns `False` (even for `>` operator).

**Boolean Handling:** Numeric comparisons (`>`, `<`, `>=`, `<=`) explicitly exclude boolean types despite Python treating `True` as 1 and `False` as 0. Equality operators (`==`, `!=`) allow booleans.

**Examples:**
```json
{"condition": "context.age > 18", "target_node": "adult_flow"}
{"condition": "context.status == \"active\"", "target_node": "process"}
{"condition": "context.count >= 10", "target_node": "threshold_reached"}
```

**Implementation:** `conditions.py:41-52` defines operator lambdas with explicit type checks including boolean exclusion.

---

## Logical Operators

Combine multiple conditions with boolean logic. Evaluation follows operator precedence rules.

| Operator | Precedence | Behavior | Short-Circuit |
|----------|-----------|----------|---------------|
| `\|\|` | Low (evaluated first during parsing) | Returns true if ANY part is true | Yes (stops at first true) |
| `&&` | High (evaluated after `\|\|` split) | Returns true if ALL parts are true | Yes (stops at first false) |

**Precedence Example:** Expression `a && b || c` parses as `(a && b) || c` due to `||` split occurring first.

**Evaluation Order:**
1. Split by `||` first (low precedence)
2. Each part split by `&&` (high precedence)
3. Recursive evaluation of sub-expressions

**Examples:**
```json
{"condition": "context.age >= 18 && context.verified == true", "target_node": "approved"}
{"condition": "context.role == \"admin\" || context.role == \"moderator\"", "target_node": "management"}
{"condition": "context.score > 80 && context.attempts <= 3 || context.premium == true", "target_node": "success"}
```

**Implementation:** `conditions.py:98-107` shows `||` checked before `&&` to ensure correct parsing order.

---

## Variable Access

Access session context variables using dot notation. Two access patterns supported: `context.*` prefix and direct variable names.

### Access Patterns

| Pattern | Syntax | Example | Use Case |
|---------|--------|---------|----------|
| Prefixed | `context.variable_name` | `context.age > 18` | Explicit context access |
| Direct | `variable_name` | `age > 18` | Shorthand for context variables |
| Nested | `context.path.to.field` | `context.user.profile.verified` | Deep object traversal |

**Resolution:** Both patterns use `PathResolver` for null-safe navigation. Missing paths return `None` without errors.

**Examples:**
```json
{"condition": "context.user_name != null", "target_node": "greet_user"}
{"condition": "age >= 21", "target_node": "verify_age"}
{"condition": "context.cart.items.0.price > 100", "target_node": "premium_checkout"}
```

### Null-Safe Navigation

Missing variables or paths return `None` gracefully:
- `context.missing_var` → `None`
- `context.user.profile.email` (where `user` is missing) → `None`
- `context.items.5.name` (where index 5 doesn't exist) → `None`

**Implementation:** `conditions.py:172-177` uses PathResolver for `context.*` paths, `conditions.py:177` for direct variable access.

---

## Literal Values

Conditions can compare against literal values. Type determines parsing behavior.

| Type | Syntax | Examples | Parsed As |
|------|--------|----------|-----------|
| String | Quoted with `"` or `'` | `"active"`, `'pending'` | String (quotes removed) |
| Number | Digits, optional decimal | `42`, `-10`, `3.14` | int or float |
| Boolean | `true`, `false` (case-insensitive) | `true`, `True`, `FALSE` | bool |
| Null | `null`, `None` (case-insensitive) | `null`, `NULL`, `none` | None |

**Case Insensitivity:** Boolean and null literals are case-insensitive (`True`, `TRUE`, `true` all work).

**Examples:**
```json
{"condition": "context.status == \"approved\"", "target_node": "proceed"}
{"condition": "context.count > 0", "target_node": "has_items"}
{"condition": "context.verified == true", "target_node": "verified_user"}
{"condition": "context.optional_field != null", "target_node": "field_present"}
```

**Implementation:** `conditions.py:146-169` shows literal parsing logic with type detection order: null → boolean → string (quoted) → numeric.

---

## Truthy Evaluation

Single variable references (no operator) evaluate for truthiness.

| Value Type | Truthy When | Falsy When |
|------------|-------------|------------|
| Boolean | `True` | `False` |
| Number | Non-zero (including negatives) | Zero (0, 0.0) |
| String | Non-empty, not `"false"`, `"0"`, `"null"`, `"none"` | Empty string or special strings (case-insensitive) |
| Array/Dict | Non-empty | Empty |
| None | Never truthy | Always falsy |

**Special String Handling:** Strings `"false"`, `"0"`, `"null"`, `"none"` (case-insensitive) are falsy regardless of length.

**Examples:**
```json
{"condition": "context.premium", "target_node": "premium_features"}
{"condition": "context.error_message", "target_node": "show_error"}
{"condition": "context.items", "target_node": "process_items"}
```

**Implementation:** `conditions.py:213-238` defines `_is_truthy` with type-specific logic.

---

## Node-Specific Routing Rules

Each node type has specific routing requirements enforced during validation.

| Node Type | Max Routes | Allowed Conditions | Notes |
|-----------|-----------|-------------------|-------|
| TEXT | 1 | `true` | Auto-progression node |
| PROMPT | 1 | `true` | Single continuation after input |
| MENU (STATIC) | N (# of options) | `selection == 1` through `selection == N` | One route per option, 1-indexed |
| MENU (DYNAMIC) | 1 | `true` | Single route, use LOGIC_EXPRESSION after for branching |
| API_ACTION | 2 | `success`, `error` | Binary success/failure routing |
| LOGIC_EXPRESSION | 8 | Any non-empty expression | Full expression support |
| SET_VARIABLE | 1 | `true` | Auto-progression after assignments |

**Static Menu Pattern:** Routes must use exact pattern `selection == N` where N is 1 to number of options. Format validated with regex `^selection == \d+$`.

**Dynamic Menu Limitation:** Cannot use conditional routing directly. Add LOGIC_EXPRESSION node after menu to route based on selected item properties extracted via `output_mapping`.

**Implementation:** `flow_validator.py:203-218` defines max routes, `flow_validator.py:220-235` defines allowed conditions per node type.

---

## Validation Rules

Conditions are validated at flow submission time. Validation occurs in `RouteConditionValidator` class.

### Route Count Validation

**Rule:** Number of routes cannot exceed node-specific maximum.

**Validation Location:** `flow_validator.py:71-92`

**Error Format:**
```json
{
  "type": "route_count_exceeded",
  "message": "STATIC MENU nodes can have at most 3 routes (one per option). Currently has 5 routes",
  "location": "nodes.menu_node_1.routes",
  "suggestion": "Remove extra routes or add more menu options. Maximum 3 routes allowed"
}
```

### Condition Format Validation

**Rule:** Condition must be valid for node type and match allowed patterns.

**Validation Location:** `flow_validator.py:94-155`

**Common Errors:**

| Error | Example | Fix |
|-------|---------|-----|
| Empty condition on LOGIC_EXPRESSION | `""` | Use any valid expression (e.g., `context.age > 18`, `true`) |
| Invalid keyword for node type | `success` on PROMPT node | Use `true` for PROMPT nodes |
| Wrong STATIC MENU format | `selection = 1` | Use `selection == 1` (double equals) |
| Out of range selection | `selection == 5` (menu has 3 options) | Use `selection == 1` through `selection == 3` |

### Condition Length Constraint

**Rule:** Condition cannot exceed `MAX_ROUTE_CONDITION_LENGTH` (512 characters).

**Validation Location:** `flow_validator.py:108-115`, `flow_validator.py:994-1000`

**Constraint Source:** `SystemConstraints.MAX_ROUTE_CONDITION_LENGTH = 512`

### Duplicate Condition Detection

**Rule:** No two routes on same node can have identical conditions (case-insensitive, whitespace-normalized).

**Validation Location:** `flow_validator.py:990-1011`

**Error Format:**
```json
{
  "type": "duplicate_route_condition",
  "message": "Node 'decision_node' has duplicate route condition: 'context.age > 18'",
  "location": "nodes.decision_node.routes",
  "suggestion": "Each route must have a unique condition"
}
```

---

## Evaluation Process

The engine evaluates routes in the order they appear in the routes array. First matching condition wins.

### Evaluation Steps

1. **Iterate routes:** Process routes in array order (top to bottom in UI)
2. **Evaluate condition:** Call `ConditionEvaluator.evaluate(condition, context)`
3. **Match found:** Return first route where condition evaluates to `True`
4. **No match:** Handle based on node requirements

### No Match Behavior

**Node-Specific Handling:**

| Node Type | No Match Behavior | Code Path |
|-----------|------------------|-----------|
| API_ACTION | Raise `RoutingError` | `BaseProcessor.raise_no_matching_route()` |
| LOGIC_EXPRESSION | Raise `RoutingError` | `BaseProcessor.raise_no_matching_route()` |
| STATIC MENU | Cannot occur (validation ensures all options have routes) | N/A |
| PROMPT, TEXT, SET_VARIABLE, DYNAMIC MENU | Use single `true` route (only one route allowed) | Validation enforces single route |

**Terminal Nodes:** Nodes without any routes are terminal. Reaching a terminal node ends the session successfully.

**Implementation:** `BaseProcessor.raise_no_matching_route()` raises `RoutingError` with error code `NO_MATCHING_ROUTE` when no route matches and node requires routing.

### Error Handling

**Evaluation Errors:** If condition evaluation throws an exception, `ConditionEvaluator.evaluate()` catches it, logs details, and raises `ConditionEvaluationError`.

**Error Format:**
```python
raise ConditionEvaluationError(
    message="Condition evaluation failed",
    error_code="CONDITION_EVALUATION_ERROR",
    condition=condition
)
```

**Implementation:** `conditions.py:125-131` wraps evaluation in try-except block.

---

## Implementation Details

### Type Safety

**No Automatic Coercion:** The system performs strict type checking. Comparing incompatible types returns `False` rather than attempting conversion.

**Examples:**
- `"10" > 5` → `False` (string vs number)
- `true == 1` → `False` (boolean vs number)
- `"42" == 42` → `False` (string vs number)

**Boolean Exclusion in Numeric Comparisons:**
```python
# Implementation from conditions.py:44-51
'>': lambda a, b: (a > b if isinstance(a, (int, float)) and not isinstance(a, bool)
                   and isinstance(b, (int, float)) and not isinstance(b, bool) else False)
```

Explicitly checks `not isinstance(a, bool)` despite Python treating booleans as integers.

### Null Handling

**Equality Comparisons:** `None` can be compared with `==` and `!=` operators.

**Numeric Comparisons:** Comparing `None` with `>`, `<`, `>=`, `<=` returns `False` (not an error).

**Implementation:** `conditions.py:196-201` shows special handling for None in comparisons.

### Context Access

**PathResolver:** Both `context.*` and direct variable access use `PathResolver` for consistent null-safe navigation.

**Resolution Logic:**
- `context.variable` → Resolves to `{'context': session_context}['context']['variable']`
- `variable` → Resolves to `session_context['variable']`

**Implementation:** `conditions.py:172-177` shows resolution paths.

---

## Common Patterns

### Age Gating

```json
{
  "routes": [
    {"condition": "context.age >= 18", "target_node": "adult_content"},
    {"condition": "context.age >= 13", "target_node": "teen_content"},
    {"condition": "true", "target_node": "child_content"}
  ]
}
```

**Order Matters:** Evaluates top to bottom, first match wins. Put most specific conditions first.

### API Result Routing

```json
{
  "routes": [
    {"condition": "success", "target_node": "process_data"},
    {"condition": "error", "target_node": "handle_error"}
  ]
}
```

**Binary Split:** API_ACTION nodes always route to either `success` or `error`.

### Static Menu Selection

```json
{
  "static_options": [
    {"label": "Continue"},
    {"label": "Go Back"},
    {"label": "Cancel"}
  ],
  "routes": [
    {"condition": "selection == 1", "target_node": "continue_flow"},
    {"condition": "selection == 2", "target_node": "previous_step"},
    {"condition": "selection == 3", "target_node": "cancel_flow"}
  ]
}
```

**1-Indexed:** Selection numbering starts at 1, not 0.

### Multi-Condition Logic

```json
{
  "routes": [
    {
      "condition": "context.premium == true && context.verified == true",
      "target_node": "premium_features"
    },
    {
      "condition": "context.premium == true || context.trial_active == true",
      "target_node": "limited_features"
    },
    {
      "condition": "true",
      "target_node": "free_features"
    }
  ]
}
```

**Catch-All:** Always include a `true` route at the end for default behavior.

### Null Checks

```json
{
  "routes": [
    {"condition": "context.email != null && context.phone != null", "target_node": "full_profile"},
    {"condition": "context.email != null", "target_node": "email_only"},
    {"condition": "context.phone != null", "target_node": "phone_only"},
    {"condition": "true", "target_node": "minimal_profile"}
  ]
}
```

**Null Safety:** Check for null before accessing nested properties to avoid treating missing values as falsy.

---

## Constraints

All constraints from `SystemConstraints` class (`backend/v1/app/utils/constants/constraints.py`):

| Constraint | Value | Enforced At | Code Path |
|------------|-------|-------------|-----------|
| `MAX_ROUTE_CONDITION_LENGTH` | 512 characters | Validation | `node_configs.py:643`, `flow_validator.py:108` |
| `MAX_ROUTES_PER_NODE` | 8 | Validation | `node_configs.py:940`, `flow_validator.py:982` |
| Node-specific max routes | Varies by type | Validation | `flow_validator.py:203-218` |
| STATIC MENU max routes | Number of options (1-8) | Validation | `flow_validator.py:206-210` |
| DYNAMIC MENU max routes | 1 | Validation | `flow_validator.py:207` |
| API_ACTION max routes | 2 | Validation | `flow_validator.py:212` |
| LOGIC_EXPRESSION max routes | 8 | Validation | `flow_validator.py:214` |
| TEXT/PROMPT/SET_VARIABLE max routes | 1 | Validation | `flow_validator.py:216` |

**Route Array Order:** Preserved during validation and execution. First matching condition always wins.

**Condition String Format:** UTF-8 string, whitespace preserved in literals but trimmed for keyword matching.

**Reserved Keywords:** `success`, `error`, `true` are reserved and cannot be used as variable names in conditions without proper context access pattern.
