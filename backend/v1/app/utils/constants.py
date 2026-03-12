"""
System Constants and Constraints
Based on BOT_BUILDER_SPECIFICATIONS.md
"""

from enum import Enum


# Node Types
class NodeType(str, Enum):
    PROMPT = "PROMPT"
    MENU = "MENU"
    API_ACTION = "API_ACTION"
    LOGIC_EXPRESSION = "LOGIC_EXPRESSION"
    TEXT = "TEXT"
    SET_VARIABLE = "SET_VARIABLE"


# Session Status
class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


# Bot Status
class BotStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# Integration Status
class IntegrationStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"


# OAuth Provider
class OAuthProvider(str, Enum):
    GOOGLE = "GOOGLE"
    # Future providers: GITHUB, MICROSOFT, FACEBOOK, etc.


# Validation Types
class ValidationType(str, Enum):
    REGEX = "REGEX"
    EXPRESSION = "EXPRESSION"


# Menu Source Types
class MenuSourceType(str, Enum):
    STATIC = "STATIC"
    DYNAMIC = "DYNAMIC"


# HTTP Methods
class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


# Integration Platforms
class IntegrationPlatform(str, Enum):
    """Supported messaging platform integrations"""
    WHATSAPP = "WHATSAPP"
    TELEGRAM = "TELEGRAM"
    SLACK = "SLACK"

    @classmethod
    def values(cls):
        """Get list of all platform values"""
        return [member.value for member in cls]


# Variable Types
class VariableType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    ARRAY = "ARRAY"


# Route Condition Keywords
class RouteCondition(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TRUE = "true"
    FALSE = "false"


# System Constraints
class SystemConstraints:
    """Hard limits as per specification"""
    
    # Flow Execution
    MAX_AUTO_PROGRESSION = 10  # consecutive nodes without user input
    SESSION_TIMEOUT_MINUTES = 30  # absolute timeout from creation
    API_REQUEST_TIMEOUT = 30  # seconds, fixed
    MAX_VALIDATION_ATTEMPTS_DEFAULT = 3  # configurable per flow
    MAX_VALIDATION_ATTEMPTS_MAX = 10  # absolute maximum
    
    # Flow Structure
    MAX_NODES_PER_FLOW = 48
    MAX_ROUTES_PER_NODE = 8
    MAX_FLOW_ID_LENGTH = 96
    MAX_NODE_ID_LENGTH = 96
    MAX_VARIABLE_NAME_LENGTH = 96
    MAX_VARIABLE_DEFAULT_LENGTH = 256
    MAX_FLOW_NAME_LENGTH = 96
    
    # Bot & Flow Naming
    MAX_BOT_NAME_LENGTH = 96
    MAX_BOT_DESCRIPTION_LENGTH = 512
    
    # Content Limits
    MAX_MESSAGE_LENGTH = 1024
    MAX_ERROR_MESSAGE_LENGTH = 512
    MAX_TEMPLATE_LENGTH = 1024
    MAX_COUNTER_TEXT_LENGTH = 512
    MAX_INTERRUPT_KEYWORD_LENGTH = 96

    # Node-specific
    MAX_ASSIGNMENTS_PER_SET_VARIABLE = 8  # SET_VARIABLE: max assignments per node

    # Menu Options
    MAX_STATIC_MENU_OPTIONS = 8  # Static menus: max 8 options
    MAX_DYNAMIC_MENU_OPTIONS = 24  # Dynamic menus: max 24 options (truncate if source exceeds)
    MAX_MENU_OPTIONS = 8  # Deprecated: use MAX_STATIC_MENU_OPTIONS
    MAX_OPTION_LABEL_LENGTH = 96
    
    # Validation
    MAX_REGEX_LENGTH = 512
    MAX_EXPRESSION_LENGTH = 512
    MAX_ROUTE_CONDITION_LENGTH = 512
    
    # Context & Session
    MAX_CONTEXT_SIZE = 100 * 1024  # 100 KB
    MAX_ARRAY_LENGTH = 24
    
    # API Requests
    MAX_REQUEST_URL_LENGTH = 1024
    MAX_REQUEST_BODY_SIZE = 1 * 1024 * 1024  # 1 MB
    MAX_RESPONSE_BODY_SIZE = 1 * 1024 * 1024  # 1 MB
    MAX_HEADERS_PER_REQUEST = 10
    MAX_HEADER_NAME_LENGTH = 128
    MAX_HEADER_VALUE_LENGTH = 2048
    MAX_SOURCE_PATH_LENGTH = 256
    MAX_STATUS_CODES_INPUT_LENGTH = 100


# Special Variables
class SpecialVariables:
    """Special template variables available in specific contexts"""
    
    USER_CHANNEL_ID = "user.channel_id"  # Platform-agnostic user identifier
    USER_CHANNEL = "user.channel"  # Communication channel name
    ITEM = "item"
    INDEX = "index"
    INPUT = "input"
    CURRENT_ATTEMPT = "current_attempt"
    MAX_ATTEMPTS = "max_attempts"
    SELECTION = "selection"
    API_RESULT = "_api_result"


# Error Messages
class ErrorMessages:
    """Standard error messages"""
    
    SESSION_EXPIRED = "Session expired. Please start again."
    NO_ROUTE_MATCH = "An error occurred. Please try again."
    MAX_AUTO_PROGRESSION = "System error. Please contact support."
    FIELD_REQUIRED = "This field is required. Please enter a value."
    INVALID_SELECTION = "Invalid selection. Please choose a valid option."
    VALIDATION_FAILED = "Invalid input. Please try again."
    API_TIMEOUT = "Request timed out. Please try again."
    GENERIC_ERROR = "An error occurred. Please try again."


# Regular Expressions
class RegexPatterns:
    """Common regex patterns"""

    # Template variable pattern: {{variable}}
    TEMPLATE_VARIABLE = r'\{\{([^}]+)\}\}'

    # Identifier pattern: must start with letter or underscore, then alphanumeric/underscore
    # Valid: user_name, _temp, age, UserName
    # Invalid: 1invalid, 99bottles, -name
    IDENTIFIER = r'^[A-Za-z_][A-Za-z0-9_]*$'

    # Email validation
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # Phone number (with optional +)
    PHONE = r'^\+?[0-9]{10,15}$'

    # Numeric input validation (used in input.isNumeric())
    # Accepts: "123", "-45", "12.34", ".5"
    # Rejects: "1e10" (scientific notation), "1.2.3" (multiple decimals), "--5", "+5"
    NUMERIC_INPUT = r'^-?(\d+\.?|\d*\.\d+)$'


# Route Validation Rules
class RouteValidationRules:
    """Route validation patterns and rules"""
    
    # MENU selection pattern: "selection == N" where N is a digit
    MENU_SELECTION_PATTERN = r'^selection == \d+$'


# Reserved Keywords
class ReservedKeywords:
    """Keywords that cannot be used as variable names"""
    
    RESERVED = [
        "user",
        "item",
        "index",
        "input",
        "context",
        "response",
        "selection",
        "true",
        "false",
        "null",
        "success",
        "error",
        "_flow_variables",
        "_flow_defaults",
        "_api_result",
    ]