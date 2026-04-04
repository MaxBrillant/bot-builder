# TEXT Node

Displays a text message to the user and auto-progresses to the next node without waiting for input.

## Overview

TEXT nodes send informational messages to users without requiring a response. They process template variables from context, display the message, and immediately transition to the next node based on route evaluation.

**Source files:**
- `/home/max/Desktop/projects/bot-builder/backend/v1/app/processors/text_processor.py`
- `/home/max/Desktop/projects/bot-builder/backend/v1/app/models/node_configs.py` (lines 660-674)

## Configuration

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `type` | `"TEXT"` | Yes | Literal | Node type identifier |
| `text` | `string` | Yes | 1-1024 chars | Message to display (supports `{{variable}}` templates) |

**Example:**
```json
{
  "type": "TEXT",
  "text": "Thank you {{customer_name}}! Your order #{{order_id}} has been confirmed."
}
```

## Behavior

1. **Template Rendering**: Renders `config.text` with session context variables
   - On template error: Logs error, sends truncated fallback message to avoid flow crash
2. **Message Display**: Sends rendered message to user via webhook
3. **Terminal Check**: If node has no routes, marks as terminal and ends session
4. **Route Evaluation**: Evaluates routes array to determine next node
5. **Auto-Progression**: Immediately transitions to next node (no user input required)

**Processing flow** (`text_processor.py` lines 37-95):
```python
config: TextNodeConfig = node.config
message = template_engine.render(config.text, context)  # with error handling
terminal = check_terminal(node, context, message)       # if no routes
next_node = evaluate_routes(node.routes, context)       # determine transition
return ProcessResult(message, next_node, context)
```

## Routes

TEXT nodes evaluate routes using standard condition syntax:

| Route Type | Condition | Use Case |
|------------|-----------|----------|
| Unconditional | `"default"` or `"true"` | Single path forward |
| Context-based | `"{{order_total}} > 100"` | Conditional branching on context variables |
| Terminal | No routes array | Farewell/goodbye messages |

**Notes:**
- Routes cannot reference user input (TEXT nodes don't wait for input)
- Condition expressions evaluated against session context only
- First matching route determines next node
- If no route matches: raises `NoMatchingRouteError`

## Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max message length | 1024 chars | `SystemConstraints.MAX_MESSAGE_LENGTH` |
| Auto-progression limit | 10 consecutive non-input nodes | Enforced by engine (prevents infinite loops) |
| Template variables | `{{variable}}` syntax only | `template_engine.py` |

**Limitations:**
- Cannot wait for user input
- Cannot save to context variables
- Cannot validate anything
- Does not support retry logic (not an input node)
- Does not support interrupts (not an input node)

## Examples

### 1. Success Confirmation
```json
{
  "id": "confirm_001",
  "type": "TEXT",
  "config": {
    "type": "TEXT",
    "text": "✓ Payment processed successfully! Receipt sent to {{user_email}}."
  },
  "routes": [
    {"condition": "default", "target_node": "end_001"}
  ]
}
```

### 2. Conditional Information
```json
{
  "id": "shipping_info",
  "type": "TEXT",
  "config": {
    "type": "TEXT",
    "text": "Your order will arrive in {{estimated_days}} business days."
  },
  "routes": [
    {"condition": "{{shipping_method}} == 'express'", "target_node": "express_tracking"},
    {"condition": "default", "target_node": "standard_tracking"}
  ]
}
```

### 3. Terminal Farewell
```json
{
  "id": "goodbye",
  "type": "TEXT",
  "config": {
    "type": "TEXT",
    "text": "Thank you for contacting us. Have a great day!"
  },
  "routes": null
}
```

### 4. Error Notification
```json
{
  "id": "api_error",
  "type": "TEXT",
  "config": {
    "type": "TEXT",
    "text": "Sorry, we couldn't process your request. Error code: {{error_code}}"
  },
  "routes": [
    {"condition": "default", "target_node": "retry_prompt"}
  ]
}
```

### 5. Intermediate Status
```json
{
  "id": "processing",
  "type": "TEXT",
  "config": {
    "type": "TEXT",
    "text": "Processing your request..."
  },
  "routes": [
    {"condition": "default", "target_node": "api_call_001"}
  ]
}
```
