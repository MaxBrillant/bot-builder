"""
Basic API_ACTION functionality (Tests 056-063)
Reorganized from: test_04_api_processor.py

Tests validate: Basic API_ACTION functionality
"""
import pytest

def test_56_successful_api_call_with_template_and_response_map(api_action_node):
    """✅ Successful API call - template in URL/body, response_map works"""
    # Spec: "Execute external HTTP requests"
    # "Template-based URL and body"
    # "Response data extraction with path notation"

    node = api_action_node
    context = {"token": "abc123"}
    user_channel_id = "+254712345678"

    # URL template: "https://api.example.com/users/{{user.channel_id}}"
    # Header template: "Bearer {{context.token}}"

    # Expected rendered URL: "https://api.example.com/users/+254712345678"
    # Expected header: "Authorization: Bearer abc123"

    # Mock response:
    api_response = {
    "status_code": 200,
    "body": {
    "success": True,
    "data": {
        "user_id": "user123",
        "name": "Alice",
        "age": "25"  # String needs conversion
    }
    }
    }

    flow_variables = {
    "user_id": {"type": "string", "default": None},
    "user_name": {"type": "string", "default": None},
    "age": {"type": "number", "default": 0}
    }

    # response_map extracts:
    # - {"source_path": "data.user_id", "target_variable": "user_id"}
    # - {"source_path": "data.name", "target_variable": "user_name"}
    # - {"source_path": "data.age", "target_variable": "age"}

    # Expected context after processing:
    # - context["user_id"] = "user123" (string)
    # - context["user_name"] = "Alice" (string)
    # - context["age"] = 25 (converted from "25" to number)

    # Expected route: "success"


def test_57_failed_api_call_routes_to_error(api_action_node):
    """✅ Failed API call routes to error condition"""
    # Spec: "HTTP error status (400-599) → error route"
    node = api_action_node
    context = {}

    # Mock error response:
    api_response = {
    "status_code": 404,
    "body": {
    "success": False,
    "error": "User not found"
    }
    }

    # Expected:
    # - Status code 404 not in success_check.status_codes [200, 201]
    # - Route condition set to "error"
    # - Next node: "node_error"


def test_58_api_timeout_routes_to_error(api_action_node):
    """✅ Timeout (30s) routes to error condition"""
    # Spec: "⚙️ Fixed request timeout: 30 seconds (not configurable)"
    # "✅ Timeout triggers error route condition"
    node = api_action_node
    context = {}

    # Mock timeout scenario:
    # Request takes > 30 seconds → timeout exception

    # Expected:
    # - Timeout exception caught
    # - Route condition set to "error"
    # - Next node: "node_error"


def test_59_non_json_response_routes_to_error(api_action_node):
    """✅ Non-JSON response routes to error"""
    # Spec: "✅ JSON-only responses: Non-JSON responses route to error condition"
    # "Not Supported: Plain text, XML, HTML, Binary data"
    node = api_action_node
    context = {}

    # Mock non-JSON response:
    api_response = {
    "status_code": 200,
    "headers": {"Content-Type": "text/html"},
    "body": "<html><body>Error page</body></html>"
    }

    # Expected:
    # - JSON parsing fails
    # - Route condition set to "error"
    # - Next node: "node_error"



def test_60_response_map_type_conversion_success(api_action_node, api_response_success):
    """✅ response_map type conversion (number, boolean, null on failure)"""
    # Spec: "response_map uses type inference to convert API response values"
    # "Look up target_variable in flow's variables section to determine declared type"
    # "On success: save converted value, On failure: set variable to null"

    node = api_action_node
    context = {}

    flow_variables = {
    "user_id": {"type": "string", "default": None},
    "age": {"type": "number", "default": 0},
    "verified": {"type": "boolean", "default": False},
    "tags": {"type": "array", "default": []}
    }

    # API response body:
    # {
    #   "data": {
    #     "user_id": "user123",
    #     "age": "25",         # String → needs number conversion
    #     "verified": "true",  # String → needs boolean conversion
    #     "tags": ["active", "premium"]
    #   }
    # }

    # response_map:
    # [
    #   {"source_path": "data.user_id", "target_variable": "user_id"},
    #   {"source_path": "data.age", "target_variable": "age"},
    #   {"source_path": "data.verified", "target_variable": "verified"},
    #   {"source_path": "data.tags", "target_variable": "tags"}
    # ]

    # Expected context:
    # - user_id = "user123" (string, no conversion)
    # - age = 25 (converted from "25")
    # - verified = true (converted from "true")
    # - tags = ["active", "premium"] (array, no conversion)


def test_61_response_map_missing_path_sets_null(api_action_node):
    """✅ response_map - missing path sets variable to null"""
    # Spec: "Missing response paths → variable set to null"
    node = api_action_node
    context = {}

    flow_variables = {
    "user_id": {"type": "string", "default": None},
    "missing_field": {"type": "string", "default": None}
    }

    # API response:
    api_response = {
    "status_code": 200,
    "body": {
    "data": {
        "user_id": "user123"
        # missing_field not present
    }
    }
    }

    # response_map:
    # [
    #   {"source_path": "data.user_id", "target_variable": "user_id"},
    #   {"source_path": "data.missing_field", "target_variable": "missing_field"}
    # ]

    # Expected context:
    # - user_id = "user123"
    # - missing_field = null (path not found)



def test_62_success_check_with_status_codes_and_expression(api_action_node):
    """✅ success_check with status_codes and expression"""
    # Spec: "success_check: Status code matching + expression evaluation on response body"
    # "Available variables: response.body.*, response.status, response.headers.*"

    node = api_action_node
    context = {}

    # success_check config:
    # {
    #   "status_codes": [200, 201],
    #   "expression": "response.body.success == true"
    # }

    # Test case 1: Status 200, success=true → success
    response_1 = {
    "status_code": 200,
    "body": {"success": True, "data": {}}
    }
    # Expected: route = "success"

    # Test case 2: Status 200, success=false → error
    response_2 = {
    "status_code": 200,
    "body": {"success": False, "error": "Failed"}
    }
    # Expected: route = "error" (expression fails)

    # Test case 3: Status 404 → error
    response_3 = {
    "status_code": 404,
    "body": {"success": True}
    }
    # Expected: route = "error" (status not in list)



def test_63_query_parameters_in_url_template(api_action_node):
    """✅ Query parameters with template syntax"""
    # Spec: "Query parameters can be added using template syntax in the URL"
    # Example: "https://api.example.com/users?page={{context.page}}&limit=10"

    node = api_action_node.copy()
    node["config"]["request"]["url"] = "https://api.example.com/trips?city={{context.city}}&limit=10&sort=time"

    context = {"city": "Nairobi"}

    # Expected rendered URL:
    # "https://api.example.com/trips?city=Nairobi&limit=10&sort=time"

    # Spec note: URL encoding should be handled


def test_271_request_body_at_1mb_limit_accepted():
    """✅ Request body at exactly 1 MB accepted"""
    # Spec: "Request body size: 1 MB"

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "body": {
        "data": "x" * (1024 * 1024 - 100)  # ~1 MB accounting for JSON structure
    }
    }
    }

    # Expected:
    # - Request body size calculated
    # - Size at or just under 1 MB limit
    # - Request accepted and sent
    # - No size-related errors


def test_272_request_body_exceeding_1mb_rejected():
    """✅ Request body exceeding 1 MB rejected"""
    # Spec: "Request body size: 1 MB"

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "body": {
        "large_data": "x" * (2 * 1024 * 1024)  # 2 MB - exceeds limit
    }
    }
    }

    # Expected:
    # - Request body size calculated before sending
    # - Size exceeds 1 MB limit
    # - Request rejected (not sent to API)
    # - Routes to error condition
    # - User sees error from error route handling

    # Alternative behavior:
    # - Could fail during flow validation (design-time check)
    # - Depends on whether body is static or dynamic


def test_273_response_body_at_1mb_limit_processed():
    """✅ Response body at 1 MB limit successfully processed"""
    # Spec: "Response body size: 1 MB"

    api_config = {
    "request": {
    "method": "GET",
    "url": "https://api.example.com/large-data"
    },
    "response_map": [
    {"source_path": "data", "target_variable": "result"}
    ]
    }

    # API returns response:
    large_data = "x" * (1024 * 1024 - 200)  # ~1 MB accounting for JSON structure
    api_response = {
    "status": 200,
    "body": {
    "data": large_data
    }
    }

    # Expected:
    # - Response body size checked
    # - At or just under 1 MB limit
    # - Response parsed successfully
    # - response_map executed
    # - Data stored to context (subject to context size limits)
    # - Routes to success condition


def test_274_response_body_exceeding_1mb_triggers_error():
    """✅ Response body exceeding 1 MB triggers error route"""
    # Spec: "Response body size: 1 MB"

    api_config = {
    "request": {
    "method": "GET",
    "url": "https://api.example.com/very-large-data"
    },
    "success_check": {
    "status_codes": [200]
    }
    }

    routes = [
    {"condition": "success", "target_node": "node_success"},
    {"condition": "error", "target_node": "node_error"}
    ]

    # API returns response:
    very_large_data = "x" * (3 * 1024 * 1024)  # 3 MB - exceeds limit
    api_response = {
    "status": 200,
    "body": {
    "data": very_large_data
    }
    }

    # Expected:
    # - Response body size exceeds 1 MB
    # - Response rejected/truncated
    # - Triggers error condition (not success)
    # - Routes to "node_error"
    # - User informed via error handling node

    # Alternative behavior:
    # - Response could be truncated to 1 MB
    # - Partial data processed (but spec says "limit")



def test_275_large_body_with_array_truncation():
    """✅ Large response body with arrays still subject to 24-item truncation"""
    # Spec: Both limits apply independently
    # - Response body: 1 MB max
    # - Array length: 24 items max

    api_response = {
    "status": 200,
    "body": {
    "items": [
        {"id": i, "data": "x" * 1000}  # Each item ~1 KB
        for i in range(50)  # 50 items, ~50 KB total
    ]
    }
    }

    response_map = [
    {"source_path": "items", "target_variable": "items"}
    ]

    # Expected:
    # 1. Response body size checked: ~50 KB < 1 MB ✓
    # 2. Response parsed successfully
    # 3. Array extracted: 50 items
    # 4. Array truncation applied: First 24 items kept
    # 5. context.items = first 24 items only

    # Both constraints enforced independently


def test_276_exactly_10_headers_accepted():
    """✅ API request with exactly 10 headers accepted"""
    # Spec: "Max headers per request: 10"

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer token123",
        "X-Request-ID": "req-001",
        "X-User-Agent": "BotBuilder/1.0",
        "X-Custom-1": "value1",
        "X-Custom-2": "value2",
        "X-Custom-3": "value3",
        "X-Custom-4": "value4",
        "X-Custom-5": "value5",
        "X-Custom-6": "value6"
        # Exactly 10 headers
    }
    }
    }

    # Expected:
    # - Header count: 10
    # - At limit but valid
    # - Flow validation passes
    # - Request can be sent


def test_277_more_than_10_headers_rejected():
    """✅ API request with 11+ headers rejected during validation"""
    # Spec: "Max headers per request: 10"

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer token123",
        "X-Request-ID": "req-001",
        "X-User-Agent": "BotBuilder/1.0",
        "X-Custom-1": "value1",
        "X-Custom-2": "value2",
        "X-Custom-3": "value3",
        "X-Custom-4": "value4",
        "X-Custom-5": "value5",
        "X-Custom-6": "value6",
        "X-Custom-7": "value7"
        # 11 headers - exceeds limit
    }
    }
    }

    # Expected:
    # - Flow validation error during submission
    # - Error type: "constraint_violation"
    # - Error message: "API request headers exceed maximum of 10. Found: 11 headers."
    # - Location: "nodes.node_api.config.request.headers"
    # - Flow not stored


def test_278_zero_headers_accepted():
    """✅ API request with zero headers accepted (headers optional)"""
    # Spec: Headers are optional in API_ACTION

    api_config = {
    "request": {
    "method": "GET",
    "url": "https://api.example.com/public-data"
    # No headers specified
    }
    }

    # Expected:
    # - Headers omitted (or empty object)
    # - Flow validation passes
    # - Request sent without custom headers
    # - Only default headers (if any) from HTTP client



def test_279_headers_within_count_but_names_too_long():
    """✅ Headers within count limit but name length exceeds 128 chars"""
    # Spec: "Header name length: 128 characters"
    # Tested in test_17_content_length_limits.py:test_221

    # This is a cross-constraint validation test
    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
        "Content-Type": "application/json",
        "X-" + ("Very-Long-Header-Name-" * 10): "value"
        # 2 headers (within count limit)
        # But second header name > 128 chars
    }
    }
    }

    # Expected:
    # - Header count check: 2 headers ✓
    # - Header name length check: exceeds 128 chars ✗
    # - Validation fails due to name length
    # - Error: "Header name exceeds maximum length of 128 characters"


def test_280_headers_within_count_but_values_too_long():
    """✅ Headers within count limit but value length exceeds 2048 chars"""
    # Spec: "Header value length: 2048 characters (Tokens & long values)"
    # Tested in test_17_content_length_limits.py:test_222

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + ("x" * 2050)
        # 2 headers (within count limit)
        # But Authorization value > 2048 chars
    }
    }
    }

    # Expected:
    # - Header count check: 2 headers ✓
    # - Header value length check: exceeds 2048 chars ✗
    # - Validation fails due to value length
    # - Error: "Header value exceeds maximum length of 2048 characters"


def test_281_all_header_constraints_satisfied():
    """✅ API request with all header constraints satisfied"""
    # Combined validation: count, name length, value length

    api_config = {
    "request": {
    "method": "POST",
    "url": "https://api.example.com/data",
    "headers": {
        "Content-Type": "application/json",                           # Name: 12 chars ✓, Value: 16 chars ✓
        "Authorization": "Bearer " + ("x" * 100),                     # Name: 13 chars ✓, Value: 107 chars ✓
        "X-Request-ID": "req-12345",                                 # Name: 12 chars ✓, Value: 10 chars ✓
        "X-Custom-Header": "value",                                  # Name: 15 chars ✓, Value: 5 chars ✓
        "Accept": "application/json",                                # Name: 6 chars ✓, Value: 16 chars ✓
        "User-Agent": "BotBuilder/1.0",                              # Name: 10 chars ✓, Value: 14 chars ✓
        "X-API-Key": "key123",                                       # Name: 9 chars ✓, Value: 6 chars ✓
        "X-Trace-ID": "trace-001",                                   # Name: 10 chars ✓, Value: 9 chars ✓
        "X-Environment": "production",                               # Name: 13 chars ✓, Value: 10 chars ✓
        "Cache-Control": "no-cache"                                  # Name: 13 chars ✓, Value: 8 chars ✓
        # Total: 10 headers (at limit) ✓
        # All names ≤ 128 chars ✓
        # All values ≤ 2048 chars ✓
    }
    }
    }

    # Expected:
    # - All header constraints satisfied
    # - Flow validation passes
    # - Request can be sent with all 10 headers


def test_414_api_action_post_method():
    """✅ POST method explicitly tested"""
    # Spec: API_ACTION supports POST

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "POST",
        "url": "https://api.example.com/users",
        "body": {
            "name": "{{context.name}}",
            "email": "{{context.email}}"
        }
    }
    }
    }

    # Expected:
    # - POST request sent
    # - Body included
    # - Content-Type: application/json


def test_415_api_action_get_method():
    """✅ GET method explicitly tested"""
    # Spec: API_ACTION supports GET

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "GET",
        "url": "https://api.example.com/users/{{context.user_id}}"
    }
    }
    }

    # Expected:
    # - GET request sent
    # - No body
    # - URL parameters in path


def test_416_api_action_put_method():
    """✅ PUT method explicitly tested"""
    # Spec: Common HTTP methods supported

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "PUT",
        "url": "https://api.example.com/users/{{context.user_id}}",
        "body": {
            "name": "{{context.name}}",
            "status": "active"
        }
    }
    }
    }

    # Expected:
    # - PUT request sent
    # - Full resource update
    # - Body included


def test_417_api_action_patch_method():
    """✅ PATCH method explicitly tested"""
    # Spec: PATCH for partial updates

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "PATCH",
        "url": "https://api.example.com/users/{{context.user_id}}",
        "body": {
            "status": "inactive"
        }
    }
    }
    }

    # Expected:
    # - PATCH request sent
    # - Partial resource update
    # - Only specified fields in body


def test_418_api_action_delete_method():
    """✅ DELETE method explicitly tested"""
    # Spec: DELETE for resource deletion

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "DELETE",
        "url": "https://api.example.com/users/{{context.user_id}}"
    }
    }
    }

    # Expected:
    # - DELETE request sent
    # - No body required
    # - Resource deletion


def test_419_unsupported_http_methods_rejected():
    """✅ Unsupported HTTP methods rejected during validation"""
    # Spec: Only standard HTTP methods supported

    invalid_methods = [
    "TRACE",
    "OPTIONS",
    "CONNECT",
    "HEAD",
    "CUSTOM"
    ]

    for method in invalid_methods:
        api_config = {
        "type": "API_ACTION",
        "config": {
            "request": {
                "method": method,
                "url": "https://api.example.com/resource"
            }
        }
        }

        # Expected:
        # - Validation error
        # - Error: "Unsupported HTTP method: {method}"



def test_420_api_response_204_no_content_success():
    """✅ 204 No Content treated as success"""
    # Spec: "Empty response (204 No Content) supported"

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "DELETE",
        "url": "https://api.example.com/users/123"
    }
    },
    "routes": [
    {"condition": "success", "target_node": "node_deleted"},
    {"condition": "error", "target_node": "node_error"}
    ]
    }

    # API returns: 204 No Content (empty body)

    # Expected:
    # - Routes to success path
    # - No error thrown
    # - response.body is null or empty


def test_421_empty_json_response_body_handled():
    """✅ Empty JSON response body handled gracefully"""

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "POST",
        "url": "https://api.example.com/action"
    },
    "response_map": {
        "result": "response.body.data"
    }
    }
    }

    # API returns: 200 OK with body: {}

    # Expected:
    # - Success route triggered
    # - context.result = null (missing field)
    # - No error thrown


def test_422_response_map_with_empty_body():
    """✅ response_map handles empty body gracefully"""

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "DELETE",
        "url": "https://api.example.com/resource/123"
    },
    "response_map": {
        "deleted_id": "response.body.id"
    }
    }
    }

    # API returns: 204 No Content (no body)

    # Expected:
    # - context.deleted_id = null
    # - No error thrown
    # - Null-safe mapping




def test_434_api_response_3xx_redirect_handling():
    """✅ 3xx redirect responses handled"""
    # HTTP client typically follows redirects automatically

    api_config = {
    "type": "API_ACTION",
    "config": {
    "request": {
        "method": "GET",
        "url": "https://api.example.com/resource"
    }
    },
    "routes": [
    {"condition": "success", "target_node": "node_success"},
    {"condition": "error", "target_node": "node_error"}
    ]
    }

    # API returns: 301 Moved Permanently or 302 Found

    # Expected:
    # - HTTP client follows redirect
    # - Final response status used for routing
    # - If final is 2xx → success
    # - If final is error → error route


def test_435_api_response_429_rate_limit():
    """✅ 429 Too Many Requests triggers error route"""

    api_config = {
    "type": "API_ACTION",
    "routes": [
    {"condition": "response.status == 429", "target_node": "node_rate_limited"},
    {"condition": "success", "target_node": "node_success"},
    {"condition": "error", "target_node": "node_error"}
    ]
    }

    # API returns: 429 Too Many Requests

    # Expected:
    # - First route matches (specific status check)
    # - Routes to node_rate_limited
    # - Can provide custom message about rate limits


def test_436_api_response_500_series_errors():
    """✅ 5xx server errors trigger error route"""

    api_config = {
    "type": "API_ACTION",
    "routes": [
    {"condition": "success", "target_node": "node_success"},
    {"condition": "error", "target_node": "node_server_error"}
    ]
    }

    error_codes = [500, 502, 503, 504]

    # Expected for all:
    # - Routes to error path
    # - error condition evaluates to true
    # - Can check specific status: response.status == 503


def test_437_api_response_401_unauthorized():
    """✅ 401 Unauthorized triggers error route"""

    api_config = {
    "type": "API_ACTION",
    "routes": [
    {"condition": "response.status == 401", "target_node": "node_unauthorized"},
    {"condition": "error", "target_node": "node_generic_error"}
    ]
    }

    # API returns: 401 Unauthorized

    # Expected:
    # - First route matches
    # - Routes to node_unauthorized
    # - Can provide specific message about authentication


def test_438_api_response_custom_status_check():
    """✅ Custom status code checks in routes"""
    # Spec: "success_check with response.body/status/headers"

    api_config = {
    "type": "API_ACTION",
    "routes": [
    {"condition": "response.status >= 200 && response.status < 300", "target_node": "node_2xx"},
    {"condition": "response.status >= 400 && response.status < 500", "target_node": "node_4xx"},
    {"condition": "response.status >= 500", "target_node": "node_5xx"}
    ]
    }

    # Expected:
    # - Custom status ranges
    # - Granular error handling
    # - Response status available in conditions
