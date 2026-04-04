# Template Engine

Comprehensive documentation for `backend/v1/app/core/template_engine.py` (554 lines).

## Overview

The TemplateEngine handles variable substitution in messages, URLs, and other text fields using `{{variable}}` syntax. Supports dot notation, array indexing, and null-safe navigation. Missing variables display literally for debugging.

**No support for:** arithmetic, default operators (`||`), ternary, function calls, conditionals, bracket notation (`[0]`).

## Core Syntax

| Pattern | Description | Example | Result |
|---------|-------------|---------|--------|
| `{{variable}}` | Simple variable | `{{name}}` with `{"name": "John"}` | `John` |
| `{{object.property}}` | Dot notation | `{{user.name}}` with `{"user": {"name": "Alice"}}` | `Alice` |
| `{{array.0}}` | Array indexing | `{{items.0}}` with `{"items": ["a", "b"]}` | `a` |
| `{{nested.path.deep}}` | Deep nesting | `{{data.user.address.city}}` | Resolves deeply |
| `{{missing}}` | Missing variable | `{{undefined}}` with `{}` | `{{undefined}}` (literal) |

## Variable Resolution

Uses `PathResolver.resolve()` from `app/utils/shared.py` for consistent path resolution across the system.

### Resolution Behavior

| Scenario | Behavior | Example |
|----------|----------|---------|
| Variable exists | Returns value | `{{name}}` → `John` |
| Variable missing | Returns `None` → displays literal | `{{missing}}` → `{{missing}}` |
| Null in path | Returns `None` → displays literal | `{{user.name}}` where `user` is `null` → `{{user.name}}` |
| Array out of bounds | Returns `None` → displays literal | `{{items.5}}` where array length is 3 → `{{items.5}}` |

### Special Features

- **Null-safe navigation**: `{{user.address.city}}` won't crash if `user` or `address` is `null`
- **.length property**: PathResolver supports `.length` on arrays/strings (see `app/utils/shared.py`)
- **Wildcard paths**: PathResolver supports wildcard resolution (see `app/utils/shared.py`)

## Render Methods

| Method | Purpose | Output Encoding | Use Case | Code Path |
|--------|---------|-----------------|----------|-----------|
| `render()` | Plain text | None | WhatsApp, SMS, plain text messages | Line 96-126 |
| `render_html()` | HTML output | HTML escaping (`escape_html()`) | Web UIs, prevents XSS | Line 175-204 |
| `render_url()` | URL parameters | URL encoding (`quote()`) | API URLs, query params | Line 147-173 |
| `render_json_value()` | JSON bodies | Type preservation | API request bodies | Line 362-417 |
| `render_counter()` | Retry counter text | None | ONLY for `counter_text` with special variables | Line 128-145 |

### render() - Plain Text

```python
engine.render("Hello {{name}}!", {"name": "John"})
# → "Hello John!"

engine.render("Missing: {{missing}}", {})
# → "Missing: {{missing}}"
```

- No escaping applied
- Use for WhatsApp/SMS/plain text
- Returns string

### render_html() - XSS Prevention

```python
engine.render_html("Hello {{name}}!", {"name": "<script>alert('xss')</script>"})
# → "Hello &lt;script&gt;alert('xss')&lt;/script&gt;!"

engine.render_html("Comment: {{comment}}", {"comment": "It's <great>"})
# → "Comment: It&#x27;s &lt;great&gt;"
```

- HTML escapes all variable values using `escape_html()` from `app/utils/security`
- Implements Layer 2 (context-aware escaping) per spec Section 10.1
- Use for web UIs to prevent XSS

### render_url() - URL Encoding

```python
engine.render_url("https://api.example.com/user/{{phone}}", {"phone": "+254712345678"})
# → "https://api.example.com/user/%2B254712345678"

engine.render_url("https://example.com/search?q={{query}}", {"query": "hello world"})
# → "https://example.com/search?q=hello%20world"
```

- URL-encodes variable values using `quote(str(v), safe='')`
- Use for API URLs, query parameters
- Properly encodes special characters (`+`, `@`, spaces, etc.)

### render_json_value() - Type Preservation

```python
flow_vars = {"amount": {"type": "NUMBER"}}
engine.render_json_value("{{amount}}", {"amount": 500}, flow_vars)
# → 500  (int, not "500")

engine.render_json_value("{{active}}", {"active": True})
# → True  (bool, not "True")

engine.render_json_value("{{name}}", {"name": "Alice"})
# → "Alice"  (string)
```

**Type Resolution Order:**
1. Check flow variable type definition (if `flow_variables` provided)
2. Infer from actual Python value type
3. Preserve native types for JSON (number, boolean, array)

**Behavior:**
- Simple variable template (`{{variable}}` only): preserves type
- Complex template (`text {{var}} text`): falls back to string rendering
- Missing variable: returns literal template string for debugging
- Type conversion uses `TypeConverter.convert()` from `app/utils/shared.py`

**Preserved Types:**
- `bool`, `int`, `float`, `list`, `dict` → kept as-is
- Everything else → converted to string

### render_counter() - Retry Counter Text

```python
engine.render_counter("Attempt {{current_attempt}} of {{max_attempts}}", 
                      {"current_attempt": 2, "max_attempts": 3})
# → "Attempt 2 of 3"
```

- **ONLY method** that allows `{{current_attempt}}` and `{{max_attempts}}`
- Skips validation (`skip_validation=True`) to allow these special variables
- Per spec, these variables restricted to `counter_text` only
- Use exclusively for retry logic counter display

## Special/Scoped Variables

Per BOT_BUILDER_SPECIFICATIONS.md Section 5, certain variables have usage restrictions.

| Variable | Scope | Allowed In | NOT Allowed In | Validation |
|----------|-------|------------|----------------|------------|
| `{{user.channel_id}}` | User channel | API_ACTION nodes | All other nodes | `_validate_expression()` line 312-321 |
| `{{user.channel}}` | User channel | API_ACTION nodes | All other nodes | `_validate_expression()` line 312-321 |
| `{{item.*}}` | Menu iteration | MENU `item_template` | All other contexts | Spec restriction |
| `{{index}}` | Menu iteration | MENU `item_template` | All other contexts | Spec restriction |
| `{{input}}` | Validation input | PROMPT validation expressions (not templates) | Templates, prompt text, error messages | `_validate_expression()` line 312-321 |
| `{{current_attempt}}` | Retry counter | PROMPT/MENU `counter_text` | All other templates | `_validate_expression()` line 324-331 |
| `{{max_attempts}}` | Retry counter | PROMPT/MENU `counter_text` | All other templates | `_validate_expression()` line 324-331 |

### Important Distinctions

**`{{input}}` vs Validation Expressions:**
- `{{input}}` is **NOT valid template syntax**
- `input` (no braces) is only used in PROMPT validation expressions
- Validation expressions use plain JavaScript: `input.length > 5`, `input.includes("@")`
- Template syntax (`{{input}}`) will be rejected with clear error

**User Channel Variables:**
- Only available in API_ACTION nodes
- Rejected in all other node types
- Used for passing user identifiers to external APIs

**Counter Variables:**
- Only available via `render_counter()` method
- Rejected by all other render methods
- Used exclusively for retry attempt display

## Validation

### Template Validation

`validate_template(template: str)` checks syntax before rendering (line 253-290):

| Check | Description | Error |
|-------|-------------|-------|
| Balanced braces | `{{` count must equal `}}` count | `Unbalanced template braces: mismatched {{ and }}` |
| No arithmetic | No `+`, `-`, `*`, `/`, `%` | `Unsupported template syntax: arithmetic operations not allowed` |
| No default operator | No `\|\|` | `Unsupported template syntax: default value operator (\|\|) not allowed` |
| No ternary | No `? :` | `Unsupported template syntax: ternary operator (? :) not allowed` |
| No method calls | No `.method()` | `Unsupported template syntax: method calls not allowed` |
| No bracket notation | No `[0]` | `Unsupported template syntax: bracket notation not allowed. Use dot notation (e.g., items.0)` |
| No control flow | No `if`, `for`, `while`, `function`, `return`, `class`, `new` | `Unsupported template syntax: control flow keywords not allowed` |
| No `{{input}}` | Rejected in templates | `Invalid template variable: {{input}} is not allowed. The 'input' variable is only available in PROMPT validation expressions` |
| No retry counters | `{{current_attempt}}`, `{{max_attempts}}` rejected except in `render_counter()` | `Invalid template variable: {{current_attempt}} is not allowed. Retry counter variables are ONLY available in retry_logic counter_text` |

### Expression Validation

`_validate_expression(expression: str, original_template: str)` validates individual variable expressions (line 292-360):

- Rejects reserved variable `input`
- Rejects retry counter variables (except in `render_counter()`)
- Rejects unsupported operators and syntax
- Provides actionable error messages with suggestions

### Validation Bypass

- `render_counter()` sets `skip_validation=True` to allow special counter variables
- All other render methods enforce full validation

## Where Templates Get Applied

Templates are rendered in various contexts throughout the system:

### Message Nodes (SIMPLE_MESSAGE, PROMPT, MENU)

- Message text: `render()` for WhatsApp/SMS
- Error messages: `render()` for validation errors
- Menu item templates: `render()` with `{{item.*}}` and `{{index}}`
- Counter text: `render_counter()` with `{{current_attempt}}`, `{{max_attempts}}`

### API_ACTION Nodes

- Request URL: `render_url()` for proper encoding
- Request body: `render_json_value()` for type preservation
- Headers: `render()` for header values
- User channel variables: `{{user.channel_id}}`, `{{user.channel}}` allowed here

### LOGIC_EXPRESSION Nodes

- Templates not used directly in conditions
- Condition evaluation uses PathResolver for variable access

### SET_VARIABLE Nodes

- Value assignment: `render()` or `render_json_value()` depending on target type

### ROUTE Nodes

- No template rendering (routes based on keyword matching)

## Type Handling

### Number Formatting

`_format_value()` provides smart number formatting (line 519-543):

| Input | Output | Reason |
|-------|--------|--------|
| `10.0` | `"10"` | Integer display (no decimals) |
| `10.5` | `"10.5"` | Float display (with decimals) |
| `"text"` | `"text"` | String passthrough |
| `True` | `"True"` | Boolean to string |

### Type Conversion

`_convert_to_type()` converts values to declared types (line 500-517):

- Uses `TypeConverter.convert()` from `app/utils/shared.py`
- Target types: `STRING`, `NUMBER`, `BOOLEAN`, `ARRAY`
- Falls back to `_preserve_native_type()` on conversion failure

### Native Type Preservation

`_preserve_native_type()` preserves JSON-compatible types (line 483-498):

| Type | Behavior |
|------|----------|
| `bool`, `int`, `float`, `list`, `dict` | Preserved as-is |
| Everything else | Converted to string |

## Internal Implementation

### Core Methods

| Method | Purpose | Line |
|--------|---------|------|
| `_render_internal()` | Shared rendering logic for all render methods | 46-94 |
| `_resolve_path()` | Resolve dot-notation paths using PathResolver | 206-231 |
| `_extract_variables()` | Extract all `{{variable}}` patterns from template | 233-251 |
| `_extract_variable_name()` | Extract base variable name from path (last segment) | 452-481 |
| `_format_value()` | Format value for display with smart number formatting | 519-543 |

### Pattern Matching

- Regex: `r'\{\{([^}]+)\}\}'` (line 44)
- Matches `{{variable}}` patterns
- Captures content between braces
- Non-greedy to handle multiple variables in one template

## Constraints

| Constraint | Reason | Workaround |
|------------|--------|------------|
| No arithmetic (`{{a + b}}`) | Security, simplicity | Use SET_VARIABLE with pre-calculated values |
| No default operator (`{{x \|\| 'default'}}`) | Not supported | Initialize variables with defaults in flow definition |
| No ternary (`{{x ? 'yes' : 'no'}}`) | Not supported | Use LOGIC_EXPRESSION nodes for conditional logic |
| No method calls (`{{text.toUpperCase()}}`) | Security, simplicity | Transform values before storing in variables |
| No bracket notation (`{{items[0]}}`) | Syntax choice | Use dot notation: `{{items.0}}` |
| No control flow (`{{if x}}`) | Not supported | Use node types for control flow |
| `{{input}}` not in templates | Reserved for validation expressions | Validation expressions use plain `input` (no braces) |
| `{{user.channel_id}}` only in API_ACTION | Scoping restriction | Design choice per spec Section 5 |
| `{{current_attempt}}` only in counter_text | Scoping restriction | Use `render_counter()` method exclusively |
| Missing variables display literally | Debugging feature | Intentional behavior for troubleshooting |

## Error Handling

### TemplateRenderError

Raised by `app/utils/exceptions.TemplateRenderError` with detailed context:

```python
raise TemplateRenderError(
    "Unbalanced template braces: mismatched {{ and }}",
    template=original_template
)
```

### Error Scenarios

| Scenario | Error Message | Code Path |
|----------|---------------|-----------|
| Unbalanced braces | `Unbalanced template braces: mismatched {{ and }}` | Line 278-281 |
| Unsupported syntax | `Unsupported template syntax: [feature] not allowed in templates` | Line 354-360 |
| Invalid `{{input}}` | `Invalid template variable: {{input}} is not allowed. The 'input' variable is only available in PROMPT validation expressions` | Line 315-321 |
| Invalid counter variable | `Invalid template variable: {{current_attempt}} is not allowed. Retry counter variables are ONLY available in retry_logic counter_text` | Line 325-331 |
| Render failure | `Failed to render template: [error]` | Line 89-94 |

## Dependencies

| Import | Purpose | Source |
|--------|---------|--------|
| `PathResolver` | Dot-notation path resolution with null-safety | `app/utils/shared` |
| `TypeConverter` | Type conversion for JSON values | `app/utils/shared` |
| `escape_html()` | HTML escaping for XSS prevention | `app/utils/security` |
| `TemplateRenderError` | Template-specific exception | `app/utils/exceptions` |
| `get_logger()` | Structured logging | `app/utils/logger` |
| `quote()` | URL encoding | `urllib.parse` |

## Usage Examples

### Basic Variable Substitution

```python
engine = TemplateEngine()

# Simple variable
result = engine.render("Hello {{name}}!", {"name": "Alice"})
# → "Hello Alice!"

# Nested object
result = engine.render("User: {{user.name}}", {"user": {"name": "Bob"}})
# → "User: Bob"

# Array access
result = engine.render("First: {{items.0}}", {"items": ["apple", "banana"]})
# → "First: apple"
```

### URL Encoding

```python
# Special characters in URLs
url = engine.render_url(
    "https://api.example.com/user/{{phone}}/messages",
    {"phone": "+1-555-0123"}
)
# → "https://api.example.com/user/%2B1-555-0123/messages"

# Query parameters
url = engine.render_url(
    "https://api.example.com/search?q={{query}}&lang={{lang}}",
    {"query": "hello world", "lang": "en"}
)
# → "https://api.example.com/search?q=hello%20world&lang=en"
```

### JSON Type Preservation

```python
flow_vars = {
    "amount": {"type": "NUMBER"},
    "active": {"type": "BOOLEAN"}
}

# Number preservation
value = engine.render_json_value("{{amount}}", {"amount": 500}, flow_vars)
# → 500 (int, not "500")

# Boolean preservation
value = engine.render_json_value("{{active}}", {"active": True})
# → True (bool, not "True")

# Complex template falls back to string
value = engine.render_json_value("Amount: {{amount}}", {"amount": 500}, flow_vars)
# → "Amount: 500" (string)
```

### HTML Escaping

```python
# Prevent XSS
html = engine.render_html(
    "<div>Comment: {{comment}}</div>",
    {"comment": "<script>alert('xss')</script>"}
)
# → "<div>Comment: &lt;script&gt;alert('xss')&lt;/script&gt;</div>"
```

### Retry Counter

```python
# ONLY use render_counter() for counter_text
counter = engine.render_counter(
    "Attempt {{current_attempt}} of {{max_attempts}}",
    {"current_attempt": 2, "max_attempts": 3}
)
# → "Attempt 2 of 3"

# Using render() would reject these variables:
engine.render("Attempt {{current_attempt}}", {"current_attempt": 2})
# → TemplateRenderError: Invalid template variable: {{current_attempt}} is not allowed
```

### Missing Variables (Debugging)

```python
# Missing variables display literally
result = engine.render(
    "Hello {{name}}, your balance is {{balance}}",
    {"name": "Alice"}
)
# → "Hello Alice, your balance is {{balance}}"
# Note: {{balance}} displays literally because it's not in context
```

## Code Path Reference

| Feature | Method | Line Range |
|---------|--------|------------|
| Main rendering logic | `_render_internal()` | 46-94 |
| Plain text rendering | `render()` | 96-126 |
| Counter rendering | `render_counter()` | 128-145 |
| URL rendering | `render_url()` | 147-173 |
| HTML rendering | `render_html()` | 175-204 |
| Path resolution | `_resolve_path()` | 206-231 |
| Variable extraction | `_extract_variables()` | 233-251 |
| Template validation | `validate_template()` | 253-290 |
| Expression validation | `_validate_expression()` | 292-360 |
| JSON value rendering | `render_json_value()` | 362-417 |
| Variable name extraction | `_extract_variable_name()` | 452-481 |
| Native type preservation | `_preserve_native_type()` | 483-498 |
| Type conversion | `_convert_to_type()` | 500-517 |
| Value formatting | `_format_value()` | 519-543 |
| Variable presence check | `has_variables()` | 545-555 |
