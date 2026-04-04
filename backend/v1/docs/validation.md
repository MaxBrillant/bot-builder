# Flow Validation

## Overview

The flow validation system ensures flow definitions conform to structural, semantic, and constraint requirements before execution. Implemented in `/backend/v1/app/core/flow_validator.py` with constraints defined in `/backend/v1/app/utils/constants/constraints.py`.

**Validation Entry Point:** `FlowValidator.validate_flow()` - orchestrates all validation checks and returns a `ValidationResult` with errors and warnings.

**Key Components:**
- `FlowValidator` - Main orchestrator (~400 lines)
- `RouteConditionValidator` - Route-specific validation (~200 lines)
- `ValidationResult` - Error/warning accumulator (~50 lines)

---

## Validation Stages

Validation runs in 8 sequential stages. Early-stage failures short-circuit to prevent cascading errors.

| Stage | Check | Short-circuits on error |
|-------|-------|------------------------|
| 1 | Required fields present | Yes |
| 2 | Flow name format and uniqueness | No |
| 3 | Trigger keywords format and uniqueness | No |
| 4 | Flow variables and defaults | No |
| 5 | Node structure, count, Pydantic validation | Yes (if no nodes parsed) |
| 6 | Node graph: start node, orphans, cycles, unreachable nodes | No |
| 7 | Routes: targets exist, conditions valid | No |
| 8 | SET_VARIABLE assignments reference declared variables | No |

**Code Path:** `FlowValidator.validate_flow()` lines 394-445

---

## Required Fields

Top-level fields that must exist in flow JSON.

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Flow identifier (display name) |
| `trigger_keywords` | array | Keywords that activate this flow |
| `start_node_id` | string | Entry point node ID |
| `nodes` | object | Dictionary of node definitions |

**Error Type:** `missing_field`

**Code Path:** `_validate_required_fields()` lines 447-460

---

## Flow Name Validation

| Check | Rule | Error Type | Location |
|-------|------|------------|----------|
| Empty/whitespace | Cannot be empty or whitespace-only | `invalid_name` | `name` |
| Length | Max 96 characters | `constraint_violation` | `name` |
| Uniqueness | Must be unique per bot (case-sensitive) | `duplicate_flow_name` | `name` |

**Uniqueness Scope:** Per bot (not global). Update operations exclude current flow from duplicate check.

**Code Path:** `_validate_flow_name()` lines 588-630

---

## Trigger Keywords Validation

### Format Rules

| Check | Rule | Error Type | Location |
|-------|------|------------|----------|
| Type | Must be array | `invalid_type` | `trigger_keywords` |
| Count | At least 1 keyword required | `missing_trigger_keywords` | `trigger_keywords` |
| Item type | Each keyword must be string | `invalid_type` | `trigger_keywords[i]` |
| Empty values | No empty or whitespace-only strings | `invalid_value` | `trigger_keywords[i]` |
| Length | Max 96 characters per keyword | `constraint_violation` | `trigger_keywords[i]` |
| Characters | Only `A-Z`, `a-z`, `0-9`, space, `_`, `-` allowed | `invalid_characters` | `trigger_keywords[i]` |
| Wildcard | `"*"` cannot combine with other keywords | `wildcard_combination_error` | `trigger_keywords` |

**Allowed Pattern:** `^[A-Za-z0-9 _-]+$`

**Rejected Characters:** Punctuation, special characters, emojis

**Code Path:** `_validate_trigger_keywords()` lines 632-744

### Uniqueness Check

Keywords are normalized (uppercase, trimmed) before uniqueness check. Checked per bot, not globally.

**Error Type:** `duplicate_trigger_keyword`

**Query Optimization:** Batched query checks all keywords at once using `OR` conditions.

---

## Flow Variables Validation

### Variable Definition Rules

| Check | Rule | Error Type | Location |
|-------|------|------------|----------|
| Structure | `variables` must be object | `invalid_type` | `variables` |
| Reserved keywords | Cannot use reserved names | `reserved_keyword` | `variables.<name>` |
| Name format | Must match `^[A-Za-z_][A-Za-z0-9_]*$` | `invalid_format` | `variables.<name>` |
| Name length | Max 96 characters | `constraint_violation` | `variables.<name>` |
| Definition type | Each variable must be object | `invalid_structure` | `variables.<name>` |
| Type value | Must be STRING, NUMBER, BOOLEAN, or ARRAY | `invalid_type` | `variables.<name>.type` |

**Reserved Keywords:** `user`, `context`, `session`, `input` (from `ReservedKeywords.RESERVED`)

**Identifier Pattern:** `^[A-Za-z_][A-Za-z0-9_]*$` (from `RegexPatterns.IDENTIFIER`)

**Code Path:** `_validate_variables()` lines 746-795

### Default Value Type Validation

| Variable Type | Valid Default Types | Type Conversion Allowed | Error Type |
|--------------|--------------------|-----------------------|------------|
| STRING | string, null | No | `invalid_default_value` |
| NUMBER | int, float, numeric string, null | Yes (string -> number) | `invalid_default_value` |
| BOOLEAN | bool, null, "true", "false", "1", "0", "yes", "no", "y", "n" | Yes (string -> bool) | `invalid_default_value` |
| ARRAY | list, JSON array string, null | Yes (string -> JSON) | `invalid_default_value` |

**Special Cases:**
- NUMBER: Rejects booleans explicitly (common mistake)
- BOOLEAN: Rejects numeric strings not convertible to bool
- ARRAY: Validates JSON parsing for string defaults

**Code Path:** `_validate_variable_default()` lines 797-878

---

## Flow Defaults Validation

Optional `defaults` object containing global flow settings.

### Retry Logic

| Field | Type | Rule | Constraint | Error Type |
|-------|------|------|-----------|------------|
| `retry_logic` | object | Optional | - | `invalid_type` |
| `max_attempts` | int | 1 to 10 | `MAX_VALIDATION_ATTEMPTS_MAX` | `invalid_value` |
| `fail_route` | string | Optional, must exist in nodes if defined | - | `missing_node` |

**Default Behavior:** If `fail_route` not defined, session terminates on max attempts.

**Code Path:** `_validate_defaults()` lines 880-916

---

## Node Structure Validation

### Node Count and Format

| Check | Rule | Constraint | Error Type | Location |
|-------|------|-----------|------------|----------|
| Structure | `nodes` must be non-empty object | - | `invalid_structure` | `nodes` |
| Count | Max 48 nodes per flow | `MAX_NODES_PER_FLOW` | `constraint_violation` | `nodes` |
| Node ID format | Alphanumeric and underscores only | - | `invalid_format` | `nodes.<id>` |
| ID consistency | Node `id` field must match dictionary key | - | `id_mismatch` | `nodes.<id>.id` |

**Node ID Validation:** Uses `validate_node_id_format()` from `app.utils.security`

**Code Path:** `_validate_node_structure()` lines 483-546

### Pydantic Validation

Each node parsed with `FlowNode.model_validate()` which validates:
- Node type exists
- Required fields present
- Node-specific config matches schema (from `app.models.node_configs`)
- Field types correct

Validation errors from Pydantic are extracted and added to result with location path constructed from error context.

**Error Type:** `validation_error`

---

## Node Graph Validation

### Start Node

| Check | Rule | Error Type | Location | Suggestion |
|-------|------|------------|----------|-----------|
| Exists | `start_node_id` must exist in nodes | `missing_node` | `start_node_id` | Add node or change start_node_id |

**Code Path:** `_validate_node_graph()` lines 549-578

### Node Names Uniqueness

Node names must be unique within flow (case-insensitive comparison after trim).

**Error Type:** `duplicate_node_name`

**Error Format:** Reports all nodes with duplicate name

**Code Path:** `_validate_unique_node_names()` lines 918-939

### Orphan Nodes

Nodes with no parent routes (except start node) are rejected.

**Rule:** Every node except `start_node_id` must be targeted by at least one route.

**Error Type:** `orphan_nodes`

**Error Format:** Lists all orphan nodes with names and IDs

**Code Path:** `_validate_no_orphan_nodes()` lines 941-972

### Circular References

Cycles are allowed IF they contain at least one input node (PROMPT or MENU). Cycles with only non-input nodes (TEXT, API_ACTION, LOGIC_EXPRESSION, SET_VARIABLE) are rejected.

**Rationale:** Input nodes naturally break potential infinite loops by waiting for user input.

**Detection:** Depth-first search from each node, tracking visited path.

**Error Type:** `circular_reference`

**Error Format:** Shows cycle path as `node1 → node2 → node3 → node1`

**Code Path:** `_detect_circular_references()` lines 1107-1139, `_check_cycle_from_node()` lines 1084-1105

### Unreachable Nodes

Nodes not reachable from start node generate warnings (not errors).

**Detection:** Mark all nodes reachable via DFS from start, report remainder.

**Level:** Warning only

**Code Path:** `_check_unreachable_nodes()` lines 1141-1165

---

## Route Validation

### Route Structure

| Check | Rule | Constraint | Error Type | Location |
|-------|------|-----------|------------|----------|
| Route count | Max 8 routes per node | `MAX_ROUTES_PER_NODE` | `constraint_violation` | `nodes.<id>.routes` |
| Target exists | `target_node` must exist in nodes | - | `missing_node` | `nodes.<id>.routes[i].target_node` |
| Condition length | Max 512 characters | `MAX_ROUTE_CONDITION_LENGTH` | `constraint_violation` | `nodes.<id>.routes[i].condition` |
| Duplicate conditions | No duplicate conditions per node (case-insensitive) | - | `duplicate_route_condition` | `nodes.<id>.routes` |

**Code Path:** `_validate_all_routes()` lines 974-1038

### Route Count by Node Type

| Node Type | Max Routes | Calculation |
|-----------|-----------|-------------|
| PROMPT | 1 | Fixed |
| TEXT | 1 | Fixed |
| SET_VARIABLE | 1 | Fixed |
| MENU (STATIC) | N | N = number of static_options |
| MENU (DYNAMIC) | 1 | Fixed |
| API_ACTION | 2 | Fixed (success, error) |
| LOGIC_EXPRESSION | 8 | Fixed |

**Error Type:** `route_count_exceeded`

**Code Path:** `_get_max_routes()` lines 203-218, `_validate_route_count()` lines 71-92

### Route Conditions by Node Type

#### PROMPT, TEXT, SET_VARIABLE

| Valid Conditions | Count |
|-----------------|-------|
| `"true"` | 1 |

**Code Path:** `_get_allowed_conditions()` lines 220-235

#### MENU - DYNAMIC

| Valid Conditions | Count |
|-----------------|-------|
| `"true"` | 1 |

**Code Path:** `_get_allowed_conditions()` lines 223-225

#### MENU - STATIC

| Valid Pattern | Example | Range |
|--------------|---------|-------|
| `selection == N` | `selection == 1` | N ∈ [1, num_options] |

**Pattern:** `^selection == \d+$`

**Validation Steps:**
1. Regex pattern match
2. Extract numeric value
3. Check range: 1 ≤ N ≤ number of static_options

**Error Type:** `invalid_route_condition`

**Code Path:** `_validate_static_menu_condition()` lines 157-201, `MENU_SELECTION_PATTERN` line 34

#### API_ACTION

| Valid Conditions |
|-----------------|
| `"success"` |
| `"error"` |

**Code Path:** `_get_allowed_conditions()` lines 228-229

#### LOGIC_EXPRESSION

| Valid Conditions |
|-----------------|
| Any non-empty string |

**Special Rule:** Condition cannot be empty or whitespace-only. All other strings accepted (evaluated at runtime).

**Code Path:** `_validate_route_condition()` lines 118-126

**Error Type:** `invalid_route_condition`

---

## SET_VARIABLE Node Validation

Validates assignments in SET_VARIABLE nodes.

| Check | Rule | Error Type | Location | Suggestion |
|-------|------|------------|----------|-----------|
| Duplicate variables | Each variable assigned once per node | `duplicate_variable_assignment` | `nodes.<id>.config.assignments[i].variable` | Each variable once per node |
| Empty value | Value field cannot be empty | `empty_assignment_value` | `nodes.<id>.config.assignments[i].value` | Provide literal or template |
| Undeclared variable | Variable must be declared in flow `variables` | `undeclared_variable` | `nodes.<id>.config.assignments[i].variable` | Declare variable first |

**Code Path:** `_validate_set_variable_assignments()` lines 1040-1082

---

## System Constraints

All limits enforced during validation. From `/backend/v1/app/utils/constants/constraints.py`.

### Flow Structure Limits

| Constraint | Value | Enforcement Point |
|-----------|-------|------------------|
| MAX_NODES_PER_FLOW | 48 | Node structure validation |
| MAX_ROUTES_PER_NODE | 8 | Route validation |
| MAX_FLOW_NAME_LENGTH | 96 | Flow name validation |
| MAX_NODE_ID_LENGTH | 96 | Implicit (Pydantic schema) |
| MAX_VARIABLE_NAME_LENGTH | 96 | Variable validation |
| MAX_FLOW_ID_LENGTH | 96 | Database schema |

### Content Limits

| Constraint | Value | Enforcement Point |
|-----------|-------|------------------|
| MAX_MESSAGE_LENGTH | 1024 | Node config validation (Pydantic) |
| MAX_TEMPLATE_LENGTH | 1024 | Node config validation (Pydantic) |
| MAX_ERROR_MESSAGE_LENGTH | 512 | Node config validation (Pydantic) |
| MAX_COUNTER_TEXT_LENGTH | 512 | Node config validation (Pydantic) |
| MAX_INTERRUPT_KEYWORD_LENGTH | 96 | Trigger keyword validation |

### Validation Limits

| Constraint | Value | Enforcement Point |
|-----------|-------|------------------|
| MAX_REGEX_LENGTH | 512 | Node config validation (Pydantic) |
| MAX_EXPRESSION_LENGTH | 512 | Node config validation (Pydantic) |
| MAX_ROUTE_CONDITION_LENGTH | 512 | Route condition validation |

### Node-Specific Limits

| Constraint | Value | Applies To |
|-----------|-------|-----------|
| MAX_ASSIGNMENTS_PER_SET_VARIABLE | 8 | SET_VARIABLE nodes |
| MAX_STATIC_MENU_OPTIONS | 8 | MENU (STATIC) nodes |
| MAX_DYNAMIC_MENU_OPTIONS | 24 | MENU (DYNAMIC) nodes (runtime truncation) |
| MAX_OPTION_LABEL_LENGTH | 96 | MENU nodes |

### Retry Logic Limits

| Constraint | Value | Enforcement Point |
|-----------|-------|------------------|
| MAX_VALIDATION_ATTEMPTS_DEFAULT | 3 | Default value |
| MAX_VALIDATION_ATTEMPTS_MAX | 10 | Defaults validation |

### API Request Limits

| Constraint | Value | Applies To |
|-----------|-------|-----------|
| MAX_REQUEST_URL_LENGTH | 1024 | API_ACTION nodes |
| MAX_REQUEST_BODY_SIZE | 1 MB | API_ACTION nodes |
| MAX_RESPONSE_BODY_SIZE | 1 MB | API_ACTION nodes |
| MAX_HEADERS_PER_REQUEST | 10 | API_ACTION nodes |
| MAX_HEADER_NAME_LENGTH | 128 | API_ACTION nodes |
| MAX_HEADER_VALUE_LENGTH | 2048 | API_ACTION nodes |
| MAX_SOURCE_PATH_LENGTH | 256 | API_ACTION nodes |
| MAX_STATUS_CODES_INPUT_LENGTH | 100 | API_ACTION nodes |

### Runtime Limits

| Constraint | Value | Enforced At |
|-----------|-------|------------|
| MAX_AUTO_PROGRESSION | 10 | Engine execution |
| SESSION_TIMEOUT_MINUTES | 30 | Session manager |
| API_REQUEST_TIMEOUT | 30 sec | API processor |
| MAX_CONTEXT_SIZE | 100 KB | Session manager |
| MAX_ARRAY_LENGTH | 24 | Template engine |

---

## Validation Error Format

### Error Structure

```json
{
  "type": "error_type",
  "message": "Human-readable description",
  "location": "json.path.to.field",
  "suggestion": "How to fix (optional)",
  "constraint": "CONSTRAINT_NAME (optional)"
}
```

### Error Types

| Type | Meaning | Examples |
|------|---------|----------|
| `missing_field` | Required field absent | `name`, `trigger_keywords`, `start_node_id`, `nodes` |
| `invalid_type` | Wrong data type | String expected, got number |
| `invalid_value` | Value fails semantic check | Empty string, out of range |
| `invalid_format` | Format pattern mismatch | Invalid node ID characters, bad variable name |
| `invalid_name` | Name validation failure | Empty flow name |
| `invalid_characters` | Character set violation | Special chars in trigger keyword |
| `constraint_violation` | System limit exceeded | Too many nodes, string too long |
| `duplicate_flow_name` | Flow name collision | Within same bot |
| `duplicate_trigger_keyword` | Keyword collision | Within same bot |
| `duplicate_node_name` | Node name collision | Within same flow |
| `duplicate_route_condition` | Condition collision | Within same node |
| `duplicate_variable_assignment` | Variable assigned twice | In SET_VARIABLE node |
| `reserved_keyword` | Using reserved name | `user`, `context`, `session`, `input` |
| `missing_node` | Referenced node missing | start_node_id, route target, fail_route |
| `id_mismatch` | Node ID inconsistency | Key ≠ id field |
| `orphan_nodes` | Unreachable nodes | No parent routes |
| `circular_reference` | Invalid cycle | No input nodes in cycle |
| `invalid_structure` | Structure malformed | nodes not object |
| `validation_error` | Pydantic validation failed | Type/field errors from models |
| `invalid_route_condition` | Condition not allowed | Wrong format or value for node type |
| `route_count_exceeded` | Too many routes | Exceeds node type limit |
| `wildcard_combination_error` | Wildcard with other keywords | `*` must be alone |
| `invalid_default_value` | Default type mismatch | NUMBER with string default |
| `empty_assignment_value` | Assignment value empty | SET_VARIABLE node |
| `undeclared_variable` | Variable not declared | SET_VARIABLE references unknown var |

### Warning Structure

```json
{
  "message": "Human-readable description",
  "location": "json.path.to.field"
}
```

Warnings do not block flow submission. Currently only used for unreachable nodes.

---

## ValidationResult API

### Methods

```python
result = ValidationResult()

# Add error
result.add_error(
    error_type="missing_field",
    message="Required field 'name' is missing",
    location="name",                    # optional
    suggestion="Add a name field"        # optional
)

# Add warning
result.add_warning(
    message="Node 'node_2' is unreachable",
    location="nodes.node_2"
)

# Check validity
if result.is_valid():  # True if no errors (warnings OK)
    pass

# Convert to dict
response = result.to_dict()
# {
#   "valid": False,
#   "errors": [...],
#   "warnings": [...]
# }
```

**Code Path:** `ValidationResult` class lines 326-362

---

## Database Dependencies

Validation checks requiring database queries:

| Check | Query | Scope | Skipped if |
|-------|-------|-------|-----------|
| Flow name uniqueness | SELECT Flow WHERE bot_id = X AND name = Y | Per bot | `db` is None |
| Trigger keyword uniqueness | SELECT Flow WHERE bot_id = X AND trigger_keywords CONTAINS Y | Per bot | `db` is None |

**Update Mode:** Pass `current_flow_id` to exclude current flow from duplicate checks.

**Code Path:** `_validate_flow_name()` lines 607-630, `_validate_trigger_keywords()` lines 707-744

---

## Usage Example

```python
from app.core.flow_validator import FlowValidator
from uuid import UUID

validator = FlowValidator(db=session)

result = await validator.validate_flow(
    flow_data=flow_json,
    bot_id=UUID("..."),
    current_flow_id=UUID("...")  # Optional, for updates
)

if not result.is_valid():
    return JSONResponse(
        status_code=422,
        content=result.to_dict()
    )
```

**API Integration:** Used in `/backend/v1/app/api/flows.py` endpoints for create and update operations.
