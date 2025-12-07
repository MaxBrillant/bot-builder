"""
Custom Exception Classes
Defines the exception hierarchy for the Bot Builder system
"""


class BotBuilderException(Exception):
    """Base exception for all Bot Builder errors"""
    
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class ValidationError(BotBuilderException):
    """Flow validation errors"""
    
    def __init__(self, message: str = "Validation failed", errors: list = None):
        self.errors = errors or []
        super().__init__(message)


class SessionExpiredError(BotBuilderException):
    """Session timeout or expiration"""
    
    def __init__(self, message: str = "Session expired"):
        super().__init__(message)


class SessionNotFoundError(BotBuilderException):
    """Session does not exist"""
    
    def __init__(self, message: str = "Session not found"):
        super().__init__(message)


class NoMatchingRouteError(BotBuilderException):
    """No route condition matched"""
    
    def __init__(self, message: str = "No matching route found", node_id: str = None):
        self.node_id = node_id
        super().__init__(message)


class MaxAutoProgressionError(BotBuilderException):
    """Too many consecutive nodes without user input"""
    
    def __init__(self, message: str = "Maximum auto-progression limit exceeded"):
        super().__init__(message)


class MaxValidationAttemptsError(BotBuilderException):
    """Maximum validation retry attempts exceeded"""
    
    def __init__(self, message: str = "Maximum validation attempts exceeded"):
        super().__init__(message)


class APITimeoutError(BotBuilderException):
    """External API timeout"""
    
    def __init__(self, message: str = "API request timed out", url: str = None):
        self.url = url
        super().__init__(message)


class FlowNotFoundError(BotBuilderException):
    """Flow does not exist"""
    
    def __init__(self, message: str = "Flow not found", flow_id: str = None):
        self.flow_id = flow_id
        super().__init__(message)


class FlowValidationError(BotBuilderException):
    """Flow structure validation failed"""
    
    def __init__(self, message: str = "Flow validation failed", errors: list = None):
        self.errors = errors or []
        super().__init__(message)


class NodeNotFoundError(BotBuilderException):
    """Node does not exist in flow"""
    
    def __init__(self, message: str = "Node not found", node_id: str = None):
        self.node_id = node_id
        super().__init__(message)


class NotFoundError(BotBuilderException):
    """Resource not found"""
    
    def __init__(self, message: str = "Resource not found", resource_id: str = None):
        self.resource_id = resource_id
        super().__init__(message)


class UnauthorizedError(BotBuilderException):
    """User not authorized to perform action"""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message)


class AuthenticationError(BotBuilderException):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class TemplateRenderError(BotBuilderException):
    """Template rendering failed"""
    
    def __init__(self, message: str = "Template render error", template: str = None):
        self.template = template
        super().__init__(message)


class ConditionEvaluationError(BotBuilderException):
    """Condition evaluation failed"""
    
    def __init__(self, message: str = "Condition evaluation error", condition: str = None):
        self.condition = condition
        super().__init__(message)


class InvalidInputError(BotBuilderException):
    """User input validation failed"""
    
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message)


class CircularReferenceError(BotBuilderException):
    """Circular reference detected in flow"""
    
    def __init__(self, message: str = "Circular reference detected", nodes: list = None):
        self.nodes = nodes or []
        super().__init__(message)


class ConstraintViolationError(BotBuilderException):
    """System constraint violated"""
    
    def __init__(self, message: str = "Constraint violation", constraint: str = None):
        self.constraint = constraint
        super().__init__(message)


class ContextSizeExceededError(BotBuilderException):
    """Session context size exceeded limit"""
    
    def __init__(self, message: str = "Context size limit exceeded"):
        super().__init__(message)


class DuplicateFlowError(BotBuilderException):
    """Flow ID already exists"""
    
    def __init__(self, message: str = "Flow ID already exists", flow_id: str = None):
        self.flow_id = flow_id
        super().__init__(message)


class FileRestrictionError(BotBuilderException):
    """File editing restriction violated"""
    
    def __init__(self, message: str = "File editing not allowed in current mode"):
        super().__init__(message)