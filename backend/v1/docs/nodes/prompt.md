# PROMPT Node

Collects and validates user input, then saves it to a context variable.

## Overview

PROMPT nodes display a text message to the user and wait for their response. The input is validated (if configured), type-converted based on the target variable definition, and stored in the session context for use by subsequent nodes.

Use PROMPT nodes whenever you need to collect information from the user: names, phone numbers, email addresses, quantities, or any other form of text input.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | `"PROMPT"` | Yes | - | Node type identifier |
| `text` | `string` | Yes | - | Prompt message displayed to user (supports template variables, max 1024 chars) |
| `save_to_variable` | `string` | Yes | - | Variable name to store input (must be defined in flow variables, max 96 chars) |
| `validation` | `ValidationRule` | No | `null` | Optional validation rule for input |
| `interrupts` | `Interrupt[]` | No | `null` | Optional interrupt keywords for flow exit |

### ValidationRule

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"REGEX"` \| `"EXPRESSION"` | Yes | Type of validation to perform |
| `rule` | `string` | Yes | Regex pattern (max 512 chars) or expression (max 512 chars) |
| `error_message` | `string` | Yes | Error message shown when validation fails (supports `{{variable}}` templates with fallback to unrendered text on error, max 512 chars) |

### Interrupt

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input` | `string` | Yes | Keyword that triggers interrupt (case-insensitive, max 96 chars, cannot be empty or whitespace-only) |
| `target_node` | `string` | Yes | Node ID to redirect to when interrupt is triggered (max 96 chars) |

## Behavior

### Processing Order

1. **First call (no user input)**: Renders and displays `text` to user, returns `needs_input=True`
2. **Subsequent call (with user input)**:
   - Sanitize input (trim whitespace via `BaseProcessor.sanitize_input()`)
   - Check interrupts (if matched, bypass all validation and route to `target_node`)
   - Check if input is empty
   - Run validation (if defined)
   - Convert input to target variable type
   - Save to context variable
   - Evaluate routes for next node

### Empty Input Handling

- If `validation` is defined: validation rule determines if empty input is accepted
- If `validation` is not defined: empty input is rejected with default error message `"This field is required. Please enter a value."`

### Validation

**REGEX validation** (`type: "REGEX"`):
- Pattern rendered with template variables before matching
- Matches full input against regex pattern
- Unsupported features: lookahead/lookbehind assertions, named groups

**EXPRESSION validation** (`type: "EXPRESSION"`):
- Evaluates expression in context with `input` variable set to user input
- Supported: `input.isAlpha()`, `input.isNumeric()`, `input.isDigit()`, `input.length`
- Supports: comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical operators (`&&`, `||`)
- Supports: context variable access (e.g., `input.length > context.min_length`)
- Unsupported: custom functions (parseInt, toUpperCase, includes, etc.)

### Type Conversion

After validation passes, input is converted to the target variable type using `ValidationSystem.convert_type()`:

- `STRING`: No conversion (stored as-is)
- `NUMBER`: Converts to int or float
- `BOOLEAN`: Converts "true"/"false" to boolean
- `ARRAY`: Not applicable for PROMPT nodes

Type conversion failures are treated as validation errors and count toward retry limit.

### Retry Logic

When validation fails:
1. Increment `session.validation_attempts` counter
2. If attempts <= `max_attempts`: display error message with counter text, wait for new input
3. If attempts > `max_attempts`:
   - If `fail_route` is defined: reset counter, route to fail_route node
   - If `fail_route` is not defined: reset counter, terminate session with `ERROR` status

Retry configuration comes from flow-level `defaults.retry_logic`:
- `max_attempts`: Maximum validation attempts (default: 3, range: 1-10)
- `fail_route`: Node to route to when max attempts exceeded (optional)
- `counter_text`: Template for retry counter (default: `"(Attempt {{current_attempt}} of {{max_attempts}})"`)

Counter is reset on:
- Successful validation and type conversion
- Interrupt triggered
- Max attempts reached

### Interrupts

Interrupts are checked **before** validation. When matched:
- All validation is bypassed
- Validation attempts counter is reset
- Flow routes immediately to `target_node`

Interrupt matching:
- Case-insensitive
- Exact match required (after trimming whitespace)
- Empty string `""` not allowed as interrupt keyword

### Variable Storage

Before saving:
- Checks if `save_to_variable` exists in `context._flow_variables`
- If variable doesn't exist: logs warning, skips save, continues to route evaluation
- If variable exists: converts input to variable type, saves to context

After successful save:
- Variable available in context as bare name: `{{variable_name}}`
- Can be used in templates, expressions, and routes

### Auto-progression

PROMPT nodes do **not** auto-progress. They always wait for user input unless:
- Interrupt is triggered (routes to `target_node`)
- Max validation attempts reached (routes to `fail_route` or terminates)

### Terminal Behavior

PROMPT nodes with no routes are terminal. After saving input:
- If node has routes: evaluates routes normally
- If node has no routes: returns `ProcessResult` with no `next_node` (terminal)

## Routes

Routes are evaluated **after** successful validation and variable save.

Routes can reference:
- The newly saved variable: `{{saved_variable}} == "expected_value"`
- Other context variables
- Standard route conditions: `success`, `error` (not applicable for PROMPT nodes)

If no route condition matches, engine raises `NoMatchingRouteError`.

## Constraints

- Template rendering errors in `text` or `error_message`: logs error, uses fallback text
- Variable type conversion failures: treated as validation error, counts toward retry limit
- Saving to non-existent variable: logs warning, skips save, continues to route evaluation (templates will show literal `{{variable_name}}`)
- Empty validation rule: not allowed (min_length=1)
- Empty error message: not allowed (min_length=1)
- Whitespace-only interrupt keywords: rejected at config validation
- Max message length: 1024 chars
- Max error message length: 512 chars
- Max regex pattern length: 512 chars
- Max expression length: 512 chars

## Examples

### Example 1: Simple text input with regex validation

```json
{
  "id": "collect_name",
  "name": "Collect Name",
  "type": "PROMPT",
  "config": {
    "text": "What is your name?",
    "save_to_variable": "user_name",
    "validation": {
      "type": "REGEX",
      "rule": "^[A-Za-z ]{2,50}$",
      "error_message": "Please enter a valid name (2-50 letters only)"
    }
  },
  "routes": [
    {
      "condition": "user_name != null",
      "target_node": "greet_user"
    }
  ]
}
```

### Example 2: Number input with expression validation

```json
{
  "id": "collect_quantity",
  "name": "Collect Quantity",
  "type": "PROMPT",
  "config": {
    "text": "How many items would you like? (Max: {{max_quantity}})",
    "save_to_variable": "quantity",
    "validation": {
      "type": "EXPRESSION",
      "rule": "input.isNumeric() && input > 0 && input <= context.max_quantity",
      "error_message": "Please enter a number between 1 and {{max_quantity}}"
    }
  },
  "routes": [
    {
      "condition": "quantity <= 10",
      "target_node": "process_small_order"
    },
    {
      "condition": "quantity > 10",
      "target_node": "process_large_order"
    }
  ]
}
```

### Example 3: Input with interrupts

```json
{
  "id": "collect_email",
  "name": "Collect Email",
  "type": "PROMPT",
  "config": {
    "text": "Please enter your email address (or type 'cancel' to exit)",
    "save_to_variable": "email",
    "validation": {
      "type": "REGEX",
      "rule": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "error_message": "Invalid email format. Please try again."
    },
    "interrupts": [
      {
        "input": "cancel",
        "target_node": "main_menu"
      }
    ]
  },
  "routes": [
    {
      "condition": "email != null",
      "target_node": "confirm_email"
    }
  ]
}
```

### Example 4: No validation (any non-empty input accepted)

```json
{
  "id": "collect_feedback",
  "name": "Collect Feedback",
  "type": "PROMPT",
  "config": {
    "text": "Please share your feedback:",
    "save_to_variable": "feedback"
  },
  "routes": [
    {
      "condition": "feedback != null",
      "target_node": "thank_you"
    }
  ]
}
```
