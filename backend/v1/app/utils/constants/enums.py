"""
Enum classes for system constants
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
