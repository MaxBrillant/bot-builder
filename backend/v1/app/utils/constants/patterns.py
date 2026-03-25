"""
Patterns, error messages, and special variables
"""


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
