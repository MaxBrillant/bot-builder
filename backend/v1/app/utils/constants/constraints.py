"""
System constraints and hard limits
Based on BOT_BUILDER_SPECIFICATIONS.md
"""


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
