# API_ACTION Node

Executes HTTP requests to external APIs with response mapping and type-aware data extraction.

## Overview

API_ACTION nodes make HTTP calls to external services, extract data from responses, and route based on success/failure conditions. The node handles template-based request construction, JSON response parsing, type-safe data extraction, SSRF protection, and automatic timeout management.

**When to use:**
- Call external REST APIs (payments, SMS, webhooks, CRM)
- Fetch dynamic data from third-party services
- Submit form data to external systems
- Integrate with authentication/authorization services

**Key characteristics:**
- Auto-progresses (no user input required)
- 30-second fixed timeout
- JSON-only responses (non-JSON routes to error)
- HTTPS-only (HTTP rejected)
- SSRF protection blocks internal/private network requests
- Response body size limit: 1 MB

## Configuration

### APIActionNodeConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"API_ACTION"` | Yes | Node type identifier |
| `request` | `APIRequestConfig` | Yes | HTTP request configuration |
| `response_map` | `List[APIResponseMapping]` | No | Data extraction mappings from response |
| `success_check` | `APISuccessCheck` | No | Custom success condition (defaults to 2xx status) |

### APIRequestConfig

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `method` | `"GET" \| "POST" \| "PUT" \| "DELETE" \| "PATCH"` | Yes | - | HTTP method |
| `url` | `string` | Yes | Max 1024 chars | Endpoint URL (supports template variables) |
| `headers` | `List[APIHeader]` | No | Max 10 headers | Custom HTTP headers |
| `body` | `string` | No | Max 1 MB after render | JSON request body (POST/PUT/PATCH only) |

**HTTPS Enforcement:** All URLs must use `https://`. HTTP requests are rejected with 400 error and route to error condition.

**Template Support:**
- URL: Variables URL-encoded automatically (`{{phone}}` with "+254712345678" becomes `%2B254712345678`)
- Headers: Variables rendered as plain text
- Body: Variables preserve native types (numbers, booleans, arrays) based on flow variable declarations

**Special Variables in API_ACTION:**
- `{{user.channel_id}}`: User's channel identifier (WhatsApp number, etc.)
- `{{user.channel}}`: Channel type (e.g., "whatsapp", "telegram")
- These are ONLY available in API_ACTION nodes, not in TEXT/PROMPT/MENU nodes

### APIHeader

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | `string` | Yes | Max 128 chars | Header name (e.g., "Authorization", "Content-Type") |
| `value` | `string` | Yes | Max 2048 chars | Header value (supports template variables) |

**Common Headers:**
```json
[
  {"name": "Authorization", "value": "Bearer {{api_token}}"},
  {"name": "Content-Type", "value": "application/json"},
  {"name": "X-API-Key", "value": "{{api_key}}"}
]
```

### APIResponseMapping

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `source_path` | `string` | Yes | Max 256 chars | JSON path to extract from response (dot notation) |
| `target_variable` | `string` | Yes | Max 96 chars | Flow variable name to store extracted value |

**Path Syntax:**
- Dict root: `"field"`, `"data.user.id"`, `"items.0.name"`
- Array root: `"*"` (entire array), `"*.0"` (first item), `"*.0.id"`
- Primitive root: `"*"` (entire value)

**Bracket notation NOT supported:** Use `items.0.id` instead of `items[0].id`

**Type Conversion:**
Type is inferred from flow variable definition (if declared). Supports automatic conversion:
- `STRING` → text value
- `NUMBER` → integer or float
- `BOOLEAN` → true/false
- `ARRAY` → list of items

**Missing/Null Handling:**
- Missing paths: preserve existing variable value (no change)
- Null values: preserve existing variable value (no change)
- Conversion failures: preserve existing variable value, log warning, continue with other mappings

**Variable Validation:**
Mappings to non-existent flow variables are skipped with warning logged.

### APISuccessCheck

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status_codes` | `List[int]` | No | HTTP status codes considered successful (e.g., `[200, 201]`) |
| `expression` | `string` | No | Condition expression to evaluate success (max 512 chars) |

**Default Behavior (no success_check):** 2xx status codes (200-299) considered success.

**Logic:**
- If only `status_codes` provided: status must match
- If only `expression` provided: expression must evaluate to `true`
- If BOTH provided: BOTH must pass (AND logic)

**Expression Context:**
```javascript
{
  "response": {
    "body": {...},           // Parsed JSON response
    "status": 200,           // HTTP status code
    "headers": {...}         // Response headers
  }
}
```

**Example Expressions:**
```javascript
response.body.status == "ok"
response.body.error_code == null
response.body.data.length > 0
```

At least one of `status_codes` or `expression` must be specified.

## Behavior

### Processing Flow

1. **Template Rendering:**
   - URL rendered with URL encoding: `{{phone}}` → `%2B254712345678`
   - Headers rendered as plain text
   - Body parsed as JSON, variables rendered with type preservation

2. **Security Validation:**
   - HTTPS enforcement: HTTP URLs rejected with 400 error
   - SSRF protection: Blocks requests to private/internal networks (10.x, 172.16.x, 192.168.x, 127.x, 169.254.x, localhost, cloud metadata endpoints)
   - DNS resolution performed before request to validate target IP

3. **HTTP Request:**
   - Timeout: 30 seconds (fixed, not configurable)
   - Client: Shared `httpx.AsyncClient` with connection pooling
   - Body: Sent as `application/json` for POST/PUT/PATCH

4. **Response Handling:**
   - JSON parsing attempted (non-JSON responses route to error)
   - HTTP 204 No Content: Treated as success, `response_map` skipped
   - Size validation: Response body must be ≤ 1 MB

5. **Success Evaluation:**
   - Default: 2xx status codes
   - Custom: Evaluate `success_check.status_codes` AND/OR `success_check.expression`

6. **Response Mapping (success only):**
   - Skipped for HTTP 204
   - Each mapping extracts value from response using dot notation
   - Type conversion based on flow variable definition
   - Missing/null values preserve existing variable value
   - Failures don't affect routing (all mappings independent)

7. **Context Updates:**
   - `{{api_result}}` set to `"success"` or `"error"`
   - Mapped variables updated with extracted values (success only)

8. **Route Evaluation:**
   - Routes evaluated based on `{{api_result}}`
   - Typical conditions: `api_result == "success"`, `api_result == "error"`

9. **Audit Logging:**
   - Logs method, base URL (query params stripped), status code, result
   - User ID masked for privacy
   - Sensitive data excluded (API keys, request bodies, full URLs)

### Auto-Progression

API_ACTION nodes **always auto-progress** to the next node based on routes. User input is not accepted and is ignored if provided.

### Terminal Behavior

If node has no routes, session terminates after API call completes (regardless of success/error).

## Routes

API_ACTION nodes typically use two routes:
- Success route: `condition: "api_result == 'success'"`
- Error route: `condition: "api_result == 'error'"`

Routes can also use other context variables set by earlier nodes or extracted via `response_map`.

**No matching route:** Session terminates if no route condition evaluates to `true`.

## Error Handling

### Error Scenarios

| Scenario | Status Code | Body | Routes To | `{{api_result}}` |
|----------|-------------|------|-----------|-----------------|
| HTTP request | 400 | `{"error": "API endpoints must use HTTPS..."}` | error | `"error"` |
| SSRF blocked | 403 | `{"error": "API endpoint not allowed..."}` | error | `"error"` |
| Timeout (30s) | 408 | `{"error": "Request timeout"}` | error | `"error"` |
| Request body too large | 413 | `{"error": "Request or response payload too large"}` | error | `"error"` |
| Connection error | 500 | `{"error": "API request failed"}` | error | `"error"` |
| Non-JSON response | Actual status | `{"error": "Response is not valid JSON"}` | error (forced) | `"error"` |
| Response too large | 413 | `{"error": "Request or response payload too large"}` | error | `"error"` |

**Error Route Required:** API_ACTION nodes should always have an error route to handle failures gracefully.

### Timeout Behavior

- Fixed 30-second timeout applies to entire request/response cycle
- Cannot be configured
- Timeout triggers error route with status 408
- No retries (retry logic not applicable to API_ACTION nodes)

## Constraints

### Size Limits

| Item | Limit | Enforcement |
|------|-------|-------------|
| Request URL | 1024 chars | Config validation |
| Request headers | 10 max | Config validation |
| Request body | 1 MB | Runtime check after template rendering |
| Response body | 1 MB | Runtime check before parsing |

### SSRF Protection

Blocked IP ranges:
- Private networks: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- Loopback: 127.0.0.0/8
- Link-local: 169.254.0.0/16 (cloud metadata endpoints)
- Reserved: 0.0.0.0/8, 100.64.0.0/10, multicast, broadcast
- IPv6 equivalents: ::1/128, fc00::/7, fe80::/10, ::ffff:0:0/96

Blocked hostnames: `localhost`, `metadata`, `metadata.google.internal`

### Response Requirements

- Content-Type: Must be JSON (non-JSON routes to error)
- Status code: Must be 100-599
- HTTP 204: Special case (empty body, skips response_map)

### Type Conversion Rules

| Flow Variable Type | Conversion Behavior |
|-------------------|---------------------|
| `STRING` | Any value converted to string |
| `NUMBER` | Strings parsed to int/float; conversion failure preserves existing value |
| `BOOLEAN` | Truthy/falsy conversion; strings "true"/"false" parsed |
| `ARRAY` | Must be list/tuple; conversion failure preserves existing value |

### Special Variable Restrictions

`{{user.channel_id}}` and `{{user.channel}}` are ONLY available in API_ACTION nodes. Using them in TEXT/PROMPT/MENU nodes renders them literally (not substituted).

## Examples

### Example 1: Payment API with Success/Error Handling

```json
{
  "type": "API_ACTION",
  "request": {
    "method": "POST",
    "url": "https://api.payment-gateway.com/v1/charge",
    "headers": [
      {"name": "Authorization", "value": "Bearer {{api_key}}"},
      {"name": "Content-Type", "value": "application/json"}
    ],
    "body": "{\"amount\": {{amount}}, \"currency\": \"USD\", \"customer_id\": \"{{customer_id}}\"}"
  },
  "success_check": {
    "status_codes": [200, 201],
    "expression": "response.body.status == 'success'"
  },
  "response_map": [
    {"source_path": "transaction_id", "target_variable": "transaction_id"},
    {"source_path": "balance", "target_variable": "balance"}
  ]
}
```

**Routes:**
```json
[
  {"condition": "api_result == 'success'", "target_node": "payment_success"},
  {"condition": "api_result == 'error'", "target_node": "payment_failed"}
]
```

### Example 2: GET Request with User Channel ID

```json
{
  "type": "API_ACTION",
  "request": {
    "method": "GET",
    "url": "https://api.crm.com/customers/{{user.channel_id}}",
    "headers": [
      {"name": "X-API-Key", "value": "{{crm_api_key}}"}
    ]
  },
  "response_map": [
    {"source_path": "name", "target_variable": "customer_name"},
    {"source_path": "tier", "target_variable": "customer_tier"},
    {"source_path": "points", "target_variable": "loyalty_points"}
  ]
}
```

**Flow Variables:**
```json
{
  "customer_name": {"type": "STRING"},
  "customer_tier": {"type": "STRING"},
  "loyalty_points": {"type": "NUMBER"}
}
```

**Note:** `loyalty_points` extracted as number (not string) because flow variable type is `NUMBER`.

### Example 3: Array Response with Dynamic Menu

```json
{
  "type": "API_ACTION",
  "request": {
    "method": "GET",
    "url": "https://api.store.com/products?category={{category}}",
    "headers": [
      {"name": "Authorization", "value": "Bearer {{store_token}}"}
    ]
  },
  "response_map": [
    {"source_path": "*", "target_variable": "products"}
  ]
}
```

**Response Example:**
```json
[
  {"id": "p1", "name": "Product A", "price": 25.99},
  {"id": "p2", "name": "Product B", "price": 39.99}
]
```

**Flow Variables:**
```json
{
  "products": {"type": "ARRAY"}
}
```

**Next Node (MENU):**
```json
{
  "type": "MENU",
  "source_type": "DYNAMIC",
  "source_variable": "products",
  "item_template": "{{item.name}} - ${{item.price}}",
  "output_mapping": [
    {"source_path": "id", "target_variable": "selected_product_id"},
    {"source_path": "price", "target_variable": "selected_price"}
  ]
}
```

### Example 4: HTTP 204 No Content

```json
{
  "type": "API_ACTION",
  "request": {
    "method": "DELETE",
    "url": "https://api.service.com/items/{{item_id}}",
    "headers": [
      {"name": "Authorization", "value": "Bearer {{token}}"}
    ]
  }
}
```

**Behavior:** API returns HTTP 204 with empty body. Node routes to success, `response_map` skipped.

### Example 5: Type Conversion

**API Response:**
```json
{
  "user": {
    "id": "12345",
    "age": 30,
    "active": true,
    "tags": ["premium", "verified"]
  }
}
```

**Config:**
```json
{
  "response_map": [
    {"source_path": "user.id", "target_variable": "user_id"},
    {"source_path": "user.age", "target_variable": "user_age"},
    {"source_path": "user.active", "target_variable": "is_active"},
    {"source_path": "user.tags", "target_variable": "user_tags"}
  ]
}
```

**Flow Variables:**
```json
{
  "user_id": {"type": "NUMBER"},
  "user_age": {"type": "NUMBER"},
  "is_active": {"type": "BOOLEAN"},
  "user_tags": {"type": "ARRAY"}
}
```

**Result:**
- `user_id` → `12345` (number, not "12345")
- `user_age` → `30` (number)
- `is_active` → `true` (boolean)
- `user_tags` → `["premium", "verified"]` (array)
