"""
Custom Exception Classes
Defines the exception hierarchy for the Bot Builder system with proper categorization

Exception Hierarchy:
- BotBuilderException (base)
  - SystemException (infrastructure/external services)
  - ValidationException (input and flow validation)
  - SessionException (session lifecycle)
  - ExecutionException (runtime execution)
  - AuthenticationException (authentication/authorization)
"""


class BotBuilderException(Exception):
    """
    Base exception for all Bot Builder errors with structured metadata

    All Bot Builder exceptions inherit from this class and support:
    - Structured error messages
    - Error codes for programmatic handling
    - Arbitrary metadata for context
    """

    def __init__(self, message: str = "An error occurred", error_code: str = None, **metadata):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.metadata = metadata
        super().__init__(self.message)


# ============================================================================
# Category 1: System/Infrastructure Exceptions
# ============================================================================

class SystemException(BotBuilderException):
    """Infrastructure and external service failures"""
    pass


class DatabaseError(SystemException):
    def __init__(self, message="Database error", **kw):
        super().__init__(message, error_code="DATABASE_ERROR", **kw)


class CacheError(SystemException):
    def __init__(self, message="Cache error", **kw):
        super().__init__(message, error_code="CACHE_ERROR", **kw)


class HTTPClientError(SystemException):
    def __init__(self, message="HTTP client error", **kw):
        super().__init__(message, error_code="HTTP_CLIENT_ERROR", **kw)


class ExternalServiceError(SystemException):
    def __init__(self, message="External service error", **kw):
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", **kw)


class APITimeoutError(SystemException):
    """External API timeout"""

    def __init__(self, message: str = "API request timed out", error_code: str = None, url: str = None, **metadata):
        super().__init__(message, error_code, url=url, **metadata)


class CircuitBreakerOpenError(SystemException):
    def __init__(self, message="Circuit breaker is open", **kw):
        super().__init__(message, error_code="CIRCUIT_BREAKER_OPEN", **kw)


class RedisUnavailableError(SystemException):
    """Raised when Redis is required but unavailable"""

    def __init__(self, feature: str, message: str = None, error_code: str = None, **metadata):
        self.feature = feature
        msg = message or f"Redis unavailable - {feature} requires Redis"
        super().__init__(msg, error_code or "REDIS_UNAVAILABLE", feature=feature, **metadata)


class SecurityServiceUnavailableError(RedisUnavailableError):
    """Security-critical Redis feature unavailable (rate limiting, token blacklist)"""

    def __init__(self, feature: str, message: str = None, error_code: str = None, **metadata):
        super().__init__(
            feature,
            message or f"Security service unavailable - {feature} requires Redis",
            error_code or "SECURITY_SERVICE_UNAVAILABLE",
            **metadata
        )


# ============================================================================
# Category 2: Validation Exceptions
# ============================================================================

class ValidationException(BotBuilderException):
    """Input and flow validation errors"""
    pass


class ValidationError(ValidationException):
    """Generic validation errors"""

    def __init__(self, message: str = "Validation failed", error_code: str = None, errors: list = None, **metadata):
        super().__init__(message, error_code, errors=errors or [], **metadata)


class FlowValidationError(ValidationException):
    """Flow structure validation failed"""

    def __init__(self, message: str = "Flow validation failed", error_code: str = None, errors: list = None, **metadata):
        super().__init__(message, error_code, errors=errors or [], **metadata)


class InputValidationError(ValidationException):
    def __init__(self, message="Invalid input", **kw):
        super().__init__(message, error_code="INPUT_VALIDATION_ERROR", **kw)


class ConstraintViolationError(ValidationException):
    """System constraint violated (max nodes, max routes, etc.)"""

    def __init__(self, message: str = "Constraint violation", error_code: str = None, constraint: str = None, **metadata):
        super().__init__(message, error_code, constraint=constraint, **metadata)


class CircularReferenceError(ValidationException):
    """Circular reference detected in flow"""

    def __init__(self, message: str = "Circular reference detected", error_code: str = None, nodes: list = None, **metadata):
        super().__init__(message, error_code, nodes=nodes or [], **metadata)


class DuplicateFlowError(ValidationException):
    """Flow name or trigger keyword already exists"""

    def __init__(self, message: str = "Duplicate flow detected", error_code: str = None, flow_id: str = None, **metadata):
        super().__init__(message, error_code, flow_id=flow_id, **metadata)


# ============================================================================
# Category 3: Session Management Exceptions
# ============================================================================

class SessionException(BotBuilderException):
    """Session lifecycle errors"""
    pass


class SessionExpiredError(SessionException):
    """Session timeout or expiration"""

    def __init__(self, message: str = "Session expired", error_code: str = None, session_id: str = None, **metadata):
        super().__init__(message, error_code, session_id=session_id, **metadata)


class SessionNotFoundError(SessionException):
    """Session does not exist"""

    def __init__(self, message: str = "Session not found", error_code: str = None, session_key: str = None, **metadata):
        super().__init__(message, error_code, session_key=session_key, **metadata)


class ContextSizeExceededError(SessionException):
    """Session context size exceeded limit"""

    def __init__(self, message: str = "Context size limit exceeded", error_code: str = None, context_size: int = None, **metadata):
        super().__init__(message, error_code, context_size=context_size, **metadata)


class SessionLockError(SessionException):
    """Session is locked by another concurrent request"""

    def __init__(self, message: str = "Session is being processed by another request", error_code: str = None, session_id: str = None, **metadata):
        super().__init__(message, error_code or "SESSION_LOCKED", session_id=session_id, **metadata)


# ============================================================================
# Category 4: Execution Exceptions
# ============================================================================

class ExecutionException(BotBuilderException):
    """Runtime flow execution errors"""
    pass


class NoMatchingRouteError(ExecutionException):
    """No route condition matched"""

    def __init__(self, message: str = "No matching route found", error_code: str = None, node_id: str = None, **metadata):
        super().__init__(message, error_code, node_id=node_id, **metadata)


class MaxAutoProgressionError(ExecutionException):
    """Too many consecutive nodes without user input"""

    def __init__(self, message: str = "Maximum auto-progression limit exceeded", error_code: str = None, limit: int = None, **metadata):
        super().__init__(message, error_code, limit=limit, **metadata)


class MaxValidationAttemptsError(ExecutionException):
    """Maximum validation retry attempts exceeded"""

    def __init__(self, message: str = "Maximum validation attempts exceeded", error_code: str = None, attempts: int = None, **metadata):
        super().__init__(message, error_code, attempts=attempts, **metadata)


class TemplateRenderError(ExecutionException):
    """Template rendering failed"""

    def __init__(self, message: str = "Template render error", error_code: str = None, template: str = None, **metadata):
        super().__init__(message, error_code, template=template, **metadata)


class ConditionEvaluationError(ExecutionException):
    """Condition evaluation failed"""

    def __init__(self, message: str = "Condition evaluation error", error_code: str = None, condition: str = None, **metadata):
        super().__init__(message, error_code, condition=condition, **metadata)


class FlowNotFoundError(ExecutionException):
    """Flow does not exist"""

    def __init__(self, message: str = "Flow not found", error_code: str = None, flow_id: str = None, **metadata):
        super().__init__(message, error_code, flow_id=flow_id, **metadata)


class NodeNotFoundError(ExecutionException):
    """Node does not exist in flow"""

    def __init__(self, message: str = "Node not found", error_code: str = None, node_id: str = None, **metadata):
        super().__init__(message, error_code, node_id=node_id, **metadata)


# ============================================================================
# Category 5: Authentication/Authorization Exceptions
# ============================================================================

class AuthenticationException(BotBuilderException):
    """Authentication and authorization errors"""
    pass


class AuthenticationError(AuthenticationException):
    def __init__(self, message="Authentication failed", **kw):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kw)


class UnauthorizedError(AuthenticationException):
    """User not authorized to perform action"""

    def __init__(self, message: str = "Unauthorized", error_code: str = None, resource_id: str = None, **metadata):
        super().__init__(message, error_code, resource_id=resource_id, **metadata)


# ============================================================================
# Category 6: Resource Not Found Exceptions
# ============================================================================

class ResourceNotFoundException(BotBuilderException):
    """Generic resource not found"""
    pass


class NotFoundError(ResourceNotFoundException):
    """Generic not found error"""

    def __init__(self, message: str = "Resource not found", error_code: str = None, resource_id: str = None, **metadata):
        super().__init__(message, error_code, resource_id=resource_id, **metadata)


class BotNotFoundError(ResourceNotFoundException):
    """Bot does not exist"""

    def __init__(self, message: str = "Bot not found", error_code: str = None, bot_id: str = None, **metadata):
        super().__init__(message, error_code, bot_id=bot_id, **metadata)


# ============================================================================
# Other Exceptions
# ============================================================================

class FileRestrictionError(BotBuilderException):
    def __init__(self, message="File editing not allowed", **kw):
        super().__init__(message, error_code="FILE_RESTRICTION_ERROR", **kw)
