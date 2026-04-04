# Error Handling

Comprehensive documentation of the Bot Builder error handling system, covering exception hierarchy, termination triggers, error response formats, and per-scenario behavior.

## Overview

The system uses a structured exception hierarchy with automatic mapping to HTTP status codes via global exception handlers. All custom exceptions inherit from `BotBuilderException` and include structured metadata for logging and debugging.

**Source files:**
- `app/utils/exceptions.py` (296 lines) — Exception hierarchy
- `app/utils/responses.py` — HTTPException helpers
- `app/api/middleware.py` — Global exception handlers
- `app/core/engine.py` — Flow execution error handling
- `app/core/session_manager.py` — Session lifecycle error handling
- `app/processors/base_processor.py` — Processor error handling

## Exception Hierarchy

All exceptions inherit from `BotBuilderException` with structured metadata:

```
BotBuilderException (base)
├── SystemException (infrastructure/external services)
│   ├── DatabaseError
│   ├── CacheError
│   ├── HTTPClientError
│   ├── ExternalServiceError
│   ├── APITimeoutError
│   ├── CircuitBreakerOpenError
│   ├── RedisUnavailableError
│   └── SecurityServiceUnavailableError (extends RedisUnavailableError)
├── ValidationException (input and flow validation)
│   ├── ValidationError
│   ├── FlowValidationError
│   ├── InputValidationError
│   ├── ConstraintViolationError
│   ├── CircularReferenceError
│   └── DuplicateFlowError
├── SessionException (session lifecycle)
│   ├── SessionExpiredError
│   ├── SessionNotFoundError
│   ├── ContextSizeExceededError
│   └── SessionLockError
├── ExecutionException (runtime flow execution)
│   ├── NoMatchingRouteError
│   ├── MaxAutoProgressionError
│   ├── MaxValidationAttemptsError
│   ├── TemplateRenderError
│   ├── ConditionEvaluationError
│   ├── FlowNotFoundError
│   └── NodeNotFoundError
├── AuthenticationException (authentication/authorization)
│   ├── AuthenticationError
│   └── UnauthorizedError
└── ResourceNotFoundException (generic not found)
    ├── NotFoundError
    └── BotNotFoundError
```

### Base Exception Structure

**File:** `app/utils/exceptions.py:15-30`

```python
class BotBuilderException(Exception):
    def __init__(self, message: str = "An error occurred", error_code: str = None, **metadata):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.metadata = metadata
```

All exceptions support:
- `message`: Human-readable error message
- `error_code`: Programmatic code (defaults to exception class name in UPPERCASE)
- `**metadata`: Arbitrary context (e.g., `session_id`, `node_id`, `flow_id`)

## HTTP Status Mapping

**File:** `app/api/middleware.py:29-367`

Global exception handlers map exception categories to HTTP status codes:

| Exception Category | HTTP Status | Handler |
|-------------------|-------------|---------|
| `ValidationException` | 400 Bad Request | `validation_exception_handler` |
| `SessionException` | 410 Gone (expired) / 404 Not Found / 400 Bad Request (other) | `session_exception_handler` |
| `ExecutionException` | 500 Internal Server Error | `execution_exception_handler` |
| `SystemException` | 503 Service Unavailable | `system_exception_handler` |
| `AuthenticationException` | 401 Unauthorized | `authentication_exception_handler` |
| `ResourceNotFoundException` | 404 Not Found | `resource_not_found_exception_handler` |
| `BotBuilderException` (catch-all) | 500 Internal Server Error | `generic_botbuilder_exception_handler` |
| `HTTPException` | Varies by status_code | `http_exception_handler` |
| `RequestValidationError` (Pydantic) | 422 Unprocessable Entity | `request_validation_exception_handler` |

### Session Exception Special Cases

**File:** `app/api/middleware.py:58-92`

```python
status_code_map = {
    SessionExpiredError: status.HTTP_410_GONE,
    SessionNotFoundError: status.HTTP_404_NOT_FOUND
}
# Default: status.HTTP_400_BAD_REQUEST
```

## Error Response Format

All error responses follow a unified format:

```json
{
  "error": "Human-readable error message",
  "error_code": "PROGRAMMATIC_CODE",
  "errors": []  // Optional: validation errors only
}
```

### Response Helpers

**File:** `app/utils/responses.py:10-71`

| Helper | Status Code | Usage |
|--------|-------------|-------|
| `error_response(status_code, detail)` | Custom | Generic error response |
| `not_found(detail)` | 404 | Resource not found |
| `forbidden(detail)` | 403 | Access denied |
| `bad_request(detail)` | 400 | Invalid input |
| `unauthorized(detail)` | 401 | Authentication required |
| `too_many_requests(detail)` | 429 | Rate limit exceeded |
| `service_unavailable(detail)` | 503 | Service down |
| `internal_server_error(detail)` | 500 | Internal error |
| `bad_gateway(detail)` | 502 | Upstream failure |

## Flow Execution Error Handling

**File:** `app/core/engine.py:1-803`

### ConversationOrchestrator Error Handling

**Location:** `engine.py:754-797`

The orchestrator's `process_message()` method catches execution errors and returns user-friendly messages:

| Exception | User Message | Session State | HTTP Status (via handler) |
|-----------|--------------|---------------|--------------------------|
| `SessionLockError` | "Your previous message is still being processed. Please wait a moment." | Active | (200 OK — caught by orchestrator, converted to user message) |
| `SessionExpiredError` | `ErrorMessages.SESSION_EXPIRED` | Ended | 410 Gone |
| `MaxAutoProgressionError` | `ErrorMessages.MAX_AUTO_PROGRESSION` | Ended | 500 Internal Server Error |
| `NoMatchingRouteError` | `ErrorMessages.NO_ROUTE_MATCH` | Ended | 500 Internal Server Error |
| Generic `Exception` | `ErrorMessages.GENERIC_ERROR` | Ended | (logged, not raised) |

**Pattern:** Orchestrator catches exceptions at the top level and converts them to user-facing messages. Session is marked as ERROR and ended.

### FlowExecutor Error Handling

**Location:** `engine.py:418-603`

The executor's `execute_flow()` method handles node processing errors:

```python
try:
    result = await self._process_single_node(...)
except Exception as e:
    self.logger.error(f"Processor error: {str(e)}", ...)
    await self.session_manager.error_session(session.session_id)
    await message_callback(ErrorMessages.GENERIC_ERROR, IS_FINAL)
    return self._build_error_response(session, ErrorMessages.GENERIC_ERROR)
```

**Behavior:**
1. Log error with node context
2. Mark session as ERROR (committed immediately)
3. Send generic error message via callback
4. Return error response dict

### Processor Factory Error Handling

**Location:** `engine.py:496-503`

```python
try:
    processor = self.processor_factory.create(node_type)
except ValueError as e:
    self.logger.error(f"Unknown node type: {node_type}", error=str(e))
    await self.session_manager.error_session(session.session_id)
    await message_callback(ErrorMessages.GENERIC_ERROR, IS_FINAL)
    return self._build_error_response(session, ErrorMessages.GENERIC_ERROR)
```

**Narrow catch:** Only catches `ValueError` from factory (unknown node type). All other exceptions propagate.

## Session Lifecycle Error Handling

**File:** `app/core/session_manager.py:1-702`

### Session Creation Errors

**Location:** `session_manager.py:52-209`

```python
try:
    # Lock existing session, delete, create new
    ...
except IntegrityError as e:
    await self.db.rollback()
    if attempt < max_retries - 1 and 'idx_unique_active_session' in str(e):
        # Retry on race condition
        continue
    raise ConstraintViolationError(...)
except Exception as e:
    await self.db.rollback()
    raise
```

**Behavior:**
- Max 2 attempts for session creation
- Retries on `IntegrityError` with unique constraint violation (race condition)
- Rollback on failure, re-raise exception
- Raises `ConstraintViolationError` after retries exhausted

**Validation:**
- Raises `ValueError("Flow snapshot missing start_node_id")` if flow_snapshot lacks start_node_id (session_manager.py:82)
- This is a critical validation error during session initialization
- Indicates malformed flow data, should be caught during flow creation/validation

### Session Lock Errors

**Location:** `session_manager.py:211-255`

```python
try:
    result = await self.db.execute(stmt.with_for_update(nowait=True))
    return result.scalar_one_or_none()
except OperationalError as e:
    if 'could not obtain lock' in str(e).lower():
        raise SessionLockError(...)
    raise
```

**Behavior:**
- Uses `SELECT FOR UPDATE NOWAIT` to prevent blocking
- Raises `SessionLockError` if row is locked by another request
- User sees "Your previous message is still being processed. Please wait."

### Context Size Validation

**Location:** `session_manager.py:271-318`

```python
context_size = len(context_json.encode('utf-8'))

if context_size > SystemConstraints.MAX_CONTEXT_SIZE:
    raise ContextSizeExceededError(...)
```

**Behavior:**
- Validates context size before saving
- Limit: 100 KB (100,000 bytes)
- Raises `ContextSizeExceededError` (400 Bad Request via handler)
- **Critical:** Prevents data integrity issues

### Auto-Progression Limit

**Location:** `session_manager.py:340-378`

```python
if new_count > SystemConstraints.MAX_AUTO_PROGRESSION:
    await self.error_session(session_id)
    raise MaxAutoProgressionError(...)
```

**Behavior:**
- Max 10 consecutive nodes without user input
- Session marked as ERROR before raising
- User sees `ErrorMessages.MAX_AUTO_PROGRESSION`

## Processor Error Handling

**File:** `app/processors/base_processor.py:1-357`

### Route Evaluation Errors

**Location:** `base_processor.py:106-159`

```python
try:
    if self.condition_evaluator.evaluate(condition, context):
        return target_node
except Exception as e:
    self.logger.error(f"Route evaluation error: {str(e)}", ...)
    continue  # Try next route
```

**Behavior:**
- Swallows route evaluation errors and continues to next route
- Logs error but does not terminate flow
- If no route matches, returns `None` (handled by engine)

### Terminal Node Detection

**Location:** `base_processor.py:316-336`

```python
def check_terminal(self, node, context: dict, message: str = None) -> Optional[ProcessResult]:
    if node.routes and len(node.routes) > 0:
        return None
    # Node has no routes — terminal
    return ProcessResult(message=message, next_node=None, context=context)
```

**Usage:** Processors call this to detect terminal nodes (no routes).

### No Matching Route

**Location:** `base_processor.py:338-356`

```python
def raise_no_matching_route(self, node) -> None:
    raise NoMatchingRouteError(...)
```

**Usage:** Processors call this when routes exist but none matched.

## Session Termination Triggers

All termination scenarios that end a session:

| Trigger | Mechanism | Session Status | User Message | HTTP Status |
|---------|-----------|----------------|--------------|-------------|
| **Natural completion** | Node has no routes, result not terminal | `COMPLETED` | Last node's message | (200 OK) |
| **Validation failure** | Max retry attempts exceeded | `ERROR` | Node's error message | (200 OK) |
| **Timeout** | 30 minutes elapsed from creation | `EXPIRED` | `SESSION_EXPIRED` | 410 Gone |
| **Max auto-progression** | 10+ consecutive non-input nodes | `ERROR` | `MAX_AUTO_PROGRESSION` | 500 Internal Server Error |
| **No matching route** | Node has routes, none matched | `ERROR` | `NO_ROUTE_MATCH` | 500 Internal Server Error |
| **Node not found** | current_node_id not in flow | `ERROR` | `NO_ROUTE_MATCH` | 500 Internal Server Error |
| **Processor error** | Exception during node processing | `ERROR` | `GENERIC_ERROR` | (200 OK) |
| **New flow start** | User triggers new flow keyword | N/A (row deleted from database) | (none — silent termination) | (200 OK) |
| **Session lock timeout** | Concurrent request race | `ACTIVE` | "Please wait a moment." | (200 OK) |

### Session Status Enum

**File:** `app/utils/constants/enums.py:18-23`

```python
class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
```

## User-Facing Error Messages

**File:** `app/utils/constants/patterns.py:21-32`

```python
class ErrorMessages:
    SESSION_EXPIRED = "Session expired. Please start again."
    NO_ROUTE_MATCH = "An error occurred. Please try again."
    MAX_AUTO_PROGRESSION = "System error. Please contact support."
    FIELD_REQUIRED = "This field is required. Please enter a value."
    INVALID_SELECTION = "Invalid selection. Please choose a valid option."
    VALIDATION_FAILED = "Invalid input. Please try again."
    API_TIMEOUT = "Request timed out. Please try again."
    GENERIC_ERROR = "An error occurred. Please try again."
```

**Pattern:** All user-facing messages are generic and do not leak implementation details.

## Flow Execution Response Format

**File:** `app/core/engine.py:231-272`

```python
def _build_response(self, session, messages, active, ended) -> Dict[str, Any]:
    return {
        "messages": messages,
        "session_active": active,
        "session_ended": ended,
        "session_id": str(session.session_id)
    }

def _build_error_response(self, session, error_message) -> Dict[str, Any]:
    return {
        "messages": [error_message],
        "session_active": False,
        "session_ended": True
        # Note: session_id is intentionally omitted in error responses
    }
```

**Normal response:**
```json
{
  "messages": ["Hello!", "Welcome to the flow."],
  "session_active": true,
  "session_ended": false,
  "session_id": "uuid-here"
}
```

**Error response:**
```json
{
  "messages": ["An error occurred. Please try again."],
  "session_active": false,
  "session_ended": true
}
```

**Note:** Error responses omit `session_id` (unlike normal responses). This is because some errors occur before a session is created or when the session is in an indeterminate state.

## Constraints & Hard Limits

**File:** `app/utils/constants/constraints.py:8-64`

All constraint violations raise `ConstraintViolationError`:

| Constraint | Limit | Enforcement | Exception |
|-----------|-------|-------------|-----------|
| Max auto-progression | 10 | Runtime (session manager) | `MaxAutoProgressionError` |
| Session timeout | 30 minutes | Periodic cleanup + pre-execution check | `SessionExpiredError` |
| Max context size | 100 KB | Pre-save validation | `ContextSizeExceededError` |
| Max array length | 24 items | Silent truncation (no error) | (none) |
| Max validation attempts | 3-10 (configurable) | Runtime (processors) | `MaxValidationAttemptsError` |
| Max nodes per flow | 48 | Pre-save validation (flow service) | `FlowValidationError` |
| Max routes per node | 8 | Pre-save validation (flow service) | `FlowValidationError` |

## Error Handling Patterns

### Pattern 1: Catch-and-Convert (Orchestrator)

**Location:** `engine.py:680-797`

```python
try:
    # Process message
    return await self.flow_executor.execute_flow(...)
except SessionLockError:
    # Convert to user-friendly message
    msg = "Your previous message is still being processed. Please wait a moment."
    return {"messages": [msg], "session_active": True, "session_ended": False}
except SpecificException:
    # Convert to error response
    await message_callback(ErrorMessages.SESSION_EXPIRED, True)
    return {"messages": [ErrorMessages.SESSION_EXPIRED], ...}
```

**Usage:** Top-level handler converts exceptions to user messages.

### Pattern 2: Fail-Fast (Session Manager)

**Location:** `session_manager.py:271-318`

```python
if context_size > SystemConstraints.MAX_CONTEXT_SIZE:
    raise ContextSizeExceededError(...)
```

**Usage:** Validate constraints and raise immediately. Let exception handler map to HTTP status.

### Pattern 3: Swallow-and-Continue (Route Evaluation)

**Location:** `base_processor.py:142-156`

```python
try:
    if self.condition_evaluator.evaluate(condition, context):
        return target_node
except Exception as e:
    self.logger.error(...)
    continue  # Try next route
```

**Usage:** Non-critical errors that should not stop execution.

### Pattern 4: Rollback-and-Retry (Session Creation)

**Location:** `session_manager.py:181-209`

```python
for attempt in range(max_retries):
    try:
        # Create session
        ...
    except IntegrityError as e:
        await self.db.rollback()
        if attempt < max_retries - 1 and 'idx_unique_active_session' in str(e):
            continue  # Retry
        raise ConstraintViolationError(...)
```

**Usage:** Handle transient race conditions with retry logic.

### Pattern 5: Narrow Exception Catch (Processor Factory)

**Location:** `engine.py:496-503`

```python
try:
    processor = self.processor_factory.create(node_type)
except ValueError as e:  # Only catch expected error
    # Handle unknown node type
    ...
```

**Usage:** Catch only expected exceptions, let unexpected ones propagate.

## Audit Logging

**Location:** Throughout engine, session manager, and processors

All critical operations log to `audit_log` table:

```python
await self.audit_log.log_session_event(
    action="session_error",
    session_id=str(session_id),
    result=AuditResult.FAILED
)
```

**Audit triggers:**
- Session created/completed/expired/error
- Flow execution started
- Node executed
- Validation retry attempted

## Security Considerations

### PII Masking

**Location:** `session_manager.py:84`

```python
masked_user_id = self.logger.mask_pii(channel_user_id, "user_id")
```

All `channel_user_id` values are masked before logging.

### Context Encryption

**Location:** `session_manager.py:306-308, 655-657`

```python
encryption = get_encryption_service()
encrypted_context = encryption.encrypt_json(context)
```

Session context is encrypted before storing in database.

### No Detail Leakage

**Location:** `middleware.py:138-144`

```python
return JSONResponse(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    content={
        "error": "Service temporarily unavailable",  # Generic message
        "error_code": exc.error_code
    }
)
```

System errors return generic messages to users, never internal details.

## Exception Handler Registration

**File:** `app/api/middleware.py:342-368`

```python
def register_exception_handlers(app):
    # FastAPI built-in exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    
    # Category handlers (most specific first)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(SessionException, session_exception_handler)
    app.add_exception_handler(ExecutionException, execution_exception_handler)
    app.add_exception_handler(SystemException, system_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_exception_handler)
    
    # Generic catch-all
    app.add_exception_handler(BotBuilderException, generic_botbuilder_exception_handler)
```

**Order matters:** More specific handlers registered first, catch-all last.

## Key Takeaways

1. **Structured hierarchy:** All exceptions inherit from `BotBuilderException` with consistent metadata
2. **Automatic mapping:** Global handlers map exception categories to HTTP status codes
3. **User-friendly messages:** Engine converts exceptions to generic error messages
4. **Session integrity:** Critical operations use transactions with rollback on failure
5. **Graceful degradation:** Non-critical errors (route evaluation) are swallowed and logged
6. **Security-first:** PII masked, context encrypted, no internal details leaked
7. **Audit trail:** All significant events logged to audit_log table
8. **Fail-fast validation:** Constraints checked early with immediate exceptions
9. **Narrow catches:** Only expected exceptions caught, unexpected ones propagate
10. **Session termination:** Multiple triggers, all lead to ERROR/EXPIRED/COMPLETED status
