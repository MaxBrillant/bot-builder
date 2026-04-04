# MENU Node

Displays numbered options (static or dynamic) and captures user selection as an integer.

## Overview

MENU nodes present a numbered list of options to users and wait for numeric selection input (1, 2, 3...). Selection is stored in the special `selection` variable as an integer (NUMBER type) for use in routing conditions. Supports static hardcoded options or dynamic options rendered from context arrays with template-based formatting.

**Node Type**: Input-collecting (requires user interaction)

**Source**: `app/processors/menu_processor.py`, `app/models/node_configs.py` (MenuNodeConfig)

## Configuration

### Required Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `text` | string | Menu prompt/header text | 1-1024 chars, supports templates |
| `source_type` | enum | Menu option source | `"STATIC"` or `"DYNAMIC"` |

### STATIC Source Configuration

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `static_options` | array | List of menu options | Required for STATIC, 1-8 options |
| `static_options[].label` | string | Option display text | 1-96 chars, supports templates |

**Notes**:
- Cannot use `output_mapping` with STATIC menus (validation error at flow creation)
- Options are numbered automatically (1, 2, 3...)

### DYNAMIC Source Configuration

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `source_variable` | string | Variable containing array | Required for DYNAMIC, max 96 chars |
| `item_template` | string | Template for rendering each item | Required for DYNAMIC, max 1024 chars |
| `output_mapping` | array | Extract fields from selected item | Optional, DYNAMIC only |
| `output_mapping[].source_path` | string | Dot notation path to extract | 1-256 chars, no bracket notation |
| `output_mapping[].target_variable` | string | Variable to store extracted value | 1-96 chars, must exist in flow variables |

**Notes**:
- Runtime limit: 24 options max (source array truncated if longer, logged at debug level)
- Template context includes `{{item.*}}`, `{{index}}`, and all session context variables
- `output_mapping` only works with DYNAMIC menus

### Optional Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `error_message` | string | Custom invalid selection error (supports `{{variable}}` templates with fallback to unrendered text on error) | System default: "Invalid selection. Please choose a valid option." |
| `interrupts` | array | Interrupt keywords for flow exit | None |
| `interrupts[].input` | string | Keyword that triggers interrupt | 1-96 chars, case-insensitive |
| `interrupts[].target_node` | string | Node to redirect to | 1-96 chars |

## Behavior

### Processing Order

1. **Build Options**: Load static options or render dynamic options from source array (truncated to 24 if needed)
2. **First Call**: Display formatted menu with numbered options, return `needs_input=True`
3. **Sanitize Input**: Clean user input via `BaseProcessor.sanitize_input()`
4. **Check Interrupts**: Match against interrupt keywords (case-insensitive), route to `target_node` if matched, reset validation attempts
5. **Validate Selection**: Must be numeric integer in range [1, N] where N = option count
6. **Handle Validation Failure**: Use retry handler with flow-level retry logic (max 3 attempts by default)
7. **Reset Attempts**: On valid selection, reset validation attempt counter
8. **Save Selection**: Store selection as integer (1-based index) in `selection` variable (NUMBER type)
9. **Apply Output Mapping**: For DYNAMIC menus only, extract fields from selected item using type inference
10. **Evaluate Routes**: Process routes using `selection` variable in conditions

### Selection Storage

The selected option number is stored in the special variable `selection`:

- **Type**: NUMBER (integer)
- **Range**: 1 to N (where N = number of options)
- **Usage**: Available in route conditions (e.g., `selection == 1`, `selection > 3`)

**Example**:
```
User selects option 3
→ context["selection"] = 3 (integer, not string)
→ Routes can check: "selection == 3", "selection >= 2"
```

### Dynamic Menu Rendering

Template context for `item_template`:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{item.*}}` | Properties of current array item | `{{item.name}}`, `{{item.id}}` |
| `{{index}}` | 1-based option number | `{{index}}. {{item.name}}` |
| `{{context_var}}` | Any session context variable | `{{user_name}}` |

**Example**:
```json
{
  "source_variable": "products",
  "item_template": "{{index}}. {{item.name}} - ${{item.price}}"
}
```

With `products = [{"name": "Widget", "price": 10}, {"name": "Gadget", "price": 20}]`:
```
1. Widget - $10
2. Gadget - $20
```

### Output Mapping with Type Inference

For DYNAMIC menus, output mapping extracts fields from the selected item and stores them in flow variables with automatic type conversion based on the variable's declared type.

**Type Conversion Rules**:

| Variable Type | Conversion Behavior |
|---------------|---------------------|
| STRING | Store as string (no conversion) |
| NUMBER | Convert to int/float, fail preserves existing value |
| BOOLEAN | Convert to bool, fail preserves existing value |
| ARRAY | Store as array, fail preserves existing value |

**Null/Missing Handling**:
- Missing fields or null values preserve existing variable value (no update)
- Non-existent target variables skip mapping with warning log

**Example**:
```json
{
  "source_variable": "users",
  "output_mapping": [
    {"source_path": "id", "target_variable": "user_id"},
    {"source_path": "profile.name", "target_variable": "user_name"},
    {"source_path": "profile.age", "target_variable": "user_age"}
  ]
}
```

With flow variables:
```json
{
  "user_id": {"type": "STRING"},
  "user_name": {"type": "STRING"},
  "user_age": {"type": "NUMBER"}
}
```

User selects item: `{"id": "123", "profile": {"name": "Alice", "age": "25"}}`
→ `user_id = "123"` (string), `user_name = "Alice"` (string), `user_age = 25` (number)

### Validation Retry Logic

Uses flow-level retry configuration (default: 3 attempts). See `RetryLogic` model.

**Failure Paths**:
1. **Within Attempts**: Re-display menu with error message and counter
2. **Max Attempts Exceeded**:
   - If `fail_route` configured: Route to specified node
   - If no `fail_route`: Terminate session with error status

**Retry Counter Display**:
- Configurable via `counter_text` template
- Default: `"(Attempt {{current_attempt}} of {{max_attempts}})"`
- Variables: `{{current_attempt}}`, `{{max_attempts}}`

## Routes

### Available Variables

| Variable | Type | Description | Example Conditions |
|----------|------|-------------|-------------------|
| `selection` | NUMBER | Selected option number (1-based) | `selection == 1`, `selection > 3`, `selection <= 5` |
| `{mapped_vars}` | varies | Variables populated by output_mapping | `user_id != null`, `user_age >= 18` |
| `{context}` | varies | All session context variables | `user_name != ""` |

### Route Evaluation

Routes are evaluated in order until first match. Selection value is available immediately after validation.

**Example Routes**:
```json
[
  {"condition": "selection == 1", "target_node": "node_option_1"},
  {"condition": "selection == 2", "target_node": "node_option_2"},
  {"condition": "selection >= 3", "target_node": "node_other_options"},
  {"condition": "true", "target_node": "node_default"}
]
```

### Terminal Behavior

MENU nodes with no routes are terminal (session ends after selection captured).

## Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max static options | 8 | `SystemConstraints.MAX_STATIC_MENU_OPTIONS` |
| Max dynamic options (runtime) | 24 | `SystemConstraints.MAX_DYNAMIC_MENU_OPTIONS` |
| Min options | 1 | Validation |
| Option label max length | 96 chars | `SystemConstraints.MAX_OPTION_LABEL_LENGTH` |
| Item template max length | 1024 chars | `SystemConstraints.MAX_TEMPLATE_LENGTH` |
| Source path max length | 256 chars | `SystemConstraints.MAX_SOURCE_PATH_LENGTH` |
| Error message max length | 512 chars | `SystemConstraints.MAX_ERROR_MESSAGE_LENGTH` |
| Interrupt keyword max length | 96 chars | `SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH` |
| Source path format | Dot notation only | No bracket notation (`[0]`) |
| Variable name pattern | `/^[a-zA-Z_][a-zA-Z0-9_]*$/` | `RegexPatterns.IDENTIFIER` |

**Reserved Keywords** (cannot be used as target variables):
- `selection`, `input`, `response`, `status_code`, `user`, `context`, `item`, `index`

**Dynamic Array Truncation**:
- Source arrays exceeding 24 items are truncated at runtime
- Logged at debug level: `"Dynamic menu source array truncated to 24 items"`

## Examples

### Example 1: Static Menu (Simple Selection)

```json
{
  "id": "menu_main",
  "type": "MENU",
  "name": "Main Menu",
  "config": {
    "text": "Select an option:",
    "source_type": "STATIC",
    "static_options": [
      {"label": "View Account"},
      {"label": "Make Payment"},
      {"label": "Contact Support"}
    ]
  },
  "routes": [
    {"condition": "selection == 1", "target_node": "node_view_account"},
    {"condition": "selection == 2", "target_node": "node_make_payment"},
    {"condition": "selection == 3", "target_node": "node_contact_support"}
  ]
}
```

**Output**:
```
Select an option:

1. View Account
2. Make Payment
3. Contact Support
```

### Example 2: Static Menu with Interrupts

```json
{
  "id": "menu_payment",
  "type": "MENU",
  "name": "Payment Menu",
  "config": {
    "text": "Choose payment method:",
    "source_type": "STATIC",
    "static_options": [
      {"label": "Credit Card"},
      {"label": "Bank Transfer"}
    ],
    "error_message": "Please enter 1 or 2 to select a payment method.",
    "interrupts": [
      {"input": "cancel", "target_node": "node_main_menu"},
      {"input": "go back", "target_node": "node_previous"}
    ]
  },
  "routes": [
    {"condition": "selection == 1", "target_node": "node_credit_card"},
    {"condition": "selection == 2", "target_node": "node_bank_transfer"}
  ]
}
```

### Example 3: Dynamic Menu (Product Selection)

```json
{
  "id": "menu_products",
  "type": "MENU",
  "name": "Product Menu",
  "config": {
    "text": "Select a product to view details:",
    "source_type": "DYNAMIC",
    "source_variable": "products",
    "item_template": "{{item.name}} - ${{item.price}}"
  },
  "routes": [
    {"condition": "selection > 0", "target_node": "node_product_details"}
  ]
}
```

**Context**:
```json
{
  "products": [
    {"id": "p1", "name": "Widget", "price": 10},
    {"id": "p2", "name": "Gadget", "price": 20}
  ]
}
```

**Output**:
```
Select a product to view details:

1. Widget - $10
2. Gadget - $20
```

After selection of option 2:
- `context["selection"] = 2`

### Example 4: Dynamic Menu with Output Mapping

```json
{
  "id": "menu_users",
  "type": "MENU",
  "name": "User Selection",
  "config": {
    "text": "Select a user:",
    "source_type": "DYNAMIC",
    "source_variable": "users",
    "item_template": "{{item.name}} ({{item.email}})",
    "output_mapping": [
      {"source_path": "id", "target_variable": "selected_user_id"},
      {"source_path": "name", "target_variable": "selected_user_name"},
      {"source_path": "profile.age", "target_variable": "selected_user_age"}
    ]
  },
  "routes": [
    {"condition": "selected_user_age >= 18", "target_node": "node_adult_menu"},
    {"condition": "selected_user_age < 18", "target_node": "node_minor_menu"}
  ]
}
```

**Context**:
```json
{
  "users": [
    {"id": "u1", "name": "Alice", "email": "alice@example.com", "profile": {"age": 25}},
    {"id": "u2", "name": "Bob", "email": "bob@example.com", "profile": {"age": 17}}
  ]
}
```

**Flow Variables**:
```json
{
  "selected_user_id": {"type": "STRING"},
  "selected_user_name": {"type": "STRING"},
  "selected_user_age": {"type": "NUMBER"}
}
```

**Output**:
```
Select a user:

1. Alice (alice@example.com)
2. Bob (bob@example.com)
```

After selection of option 1:
- `context["selection"] = 1`
- `context["selected_user_id"] = "u1"` (string)
- `context["selected_user_name"] = "Alice"` (string)
- `context["selected_user_age"] = 25` (number, converted from any input type)

### Example 5: Dynamic Menu with Template Context

```json
{
  "id": "menu_orders",
  "type": "MENU",
  "name": "Order History",
  "config": {
    "text": "Your orders, {{customer_name}}:",
    "source_type": "DYNAMIC",
    "source_variable": "orders",
    "item_template": "Order #{{item.order_id}} - {{item.status}} - ${{item.total}}"
  },
  "routes": [
    {"condition": "selection > 0", "target_node": "node_order_details"}
  ]
}
```

**Context**:
```json
{
  "customer_name": "John Doe",
  "orders": [
    {"order_id": "12345", "status": "Shipped", "total": 99.99},
    {"order_id": "12346", "status": "Pending", "total": 49.99}
  ]
}
```

**Output**:
```
Your orders, John Doe:

1. Order #12345 - Shipped - $99.99
2. Order #12346 - Pending - $49.99
```

### Example 6: Validation Retry with Custom Messages

```json
{
  "id": "menu_support",
  "type": "MENU",
  "name": "Support Menu",
  "config": {
    "text": "How can we help you today?",
    "source_type": "STATIC",
    "static_options": [
      {"label": "Technical Issue"},
      {"label": "Billing Question"},
      {"label": "General Inquiry"}
    ],
    "error_message": "Oops! That's not a valid option. Please choose 1, 2, or 3."
  },
  "routes": [
    {"condition": "selection == 1", "target_node": "node_technical"},
    {"condition": "selection == 2", "target_node": "node_billing"},
    {"condition": "selection == 3", "target_node": "node_general"}
  ]
}
```

**Flow Defaults** (flow-level configuration):
```json
{
  "retry_logic": {
    "max_attempts": 3,
    "fail_route": "node_main_menu",
    "counter_text": "(Attempt {{current_attempt}} of {{max_attempts}})"
  }
}
```

**Invalid Input Flow**:
1. User enters "technical" → Error: "Oops! That's not a valid option. Please choose 1, 2, or 3." + counter text
2. User enters "99" → Error: "Oops! That's not a valid option. Please choose 1, 2, or 3." + counter text
3. User enters "abc" → Error: "Oops! That's not a valid option. Please choose 1, 2, or 3." + counter text
4. Max attempts exceeded → Route to `node_main_menu` (or terminate if no `fail_route`)

**Note**: `{{current_attempt}}` and `{{max_attempts}}` variables are NOT available in the `error_message` template. The retry counter is appended separately by the retry handler using the flow-level `counter_text` configuration.
