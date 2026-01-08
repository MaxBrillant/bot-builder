"""
Node Configuration Models
Pydantic models for type-safe node storage and validation.

These models provide:
- Type-safe configuration for all 6 node types
- Field-level validation with constraints from system specifications
- Cross-field validation for complex rules
- Discriminated unions for polymorphic node handling
- Immutable configurations (frozen models)
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Union, Optional, List, Dict, Any
import re
from app.utils.constants import (
    NodeType,
    ValidationType,
    MenuSourceType,
    HTTPMethod,
    VariableType,
    SystemConstraints,
    ReservedKeywords,
    RegexPatterns
)


# ============================================================================
# FLOW METADATA MODELS
# ============================================================================

class VariableDefinition(BaseModel):
    """Flow variable definition with type validation"""
    type: VariableType
    default: Any = None

    @model_validator(mode='after')
    def validate_default_matches_type(self):
        """Ensure default value matches declared type and respects length constraints"""
        if self.default is None:
            return self

        # Type validators with length constraints
        if self.type == VariableType.STRING:
            if not isinstance(self.default, str):
                raise ValueError(f"Default value must be string, got {type(self.default).__name__}")
            if len(self.default) > SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH:
                raise ValueError(
                    f"String default exceeds maximum length of {SystemConstraints.MAX_VARIABLE_DEFAULT_LENGTH} characters "
                    f"(current: {len(self.default)})"
                )
        elif self.type == VariableType.NUMBER:
            if not isinstance(self.default, (int, float)):
                raise ValueError(f"Default value must be number, got {type(self.default).__name__}")
        elif self.type == VariableType.BOOLEAN:
            if not isinstance(self.default, bool):
                raise ValueError(f"Default value must be boolean, got {type(self.default).__name__}")
        elif self.type == VariableType.ARRAY:
            if not isinstance(self.default, list):
                raise ValueError(f"Default value must be array, got {type(self.default).__name__}")
            if len(self.default) > SystemConstraints.MAX_ARRAY_LENGTH:
                raise ValueError(
                    f"Array default exceeds maximum length of {SystemConstraints.MAX_ARRAY_LENGTH} items "
                    f"(current: {len(self.default)})"
                )

        return self

    model_config = {"frozen": True}


class RetryLogic(BaseModel):
    """
    Validation retry configuration

    Note: fail_route is REQUIRED when retry_logic is explicitly defined in flow JSON.
    Validation enforced in FlowValidator._validate_retry_logic()
    """
    max_attempts: int = Field(default=3, ge=1, le=10)
    fail_route: Optional[str] = Field(default=None, max_length=96, description="Node to route to when max attempts exceeded (REQUIRED when retry_logic defined)")
    counter_text: str = Field(
        default="(Attempt {{current_attempt}} of {{max_attempts}})",
        max_length=512,
        description="Template for retry counter display"
    )

    model_config = {"frozen": True}


class FlowDefaults(BaseModel):
    """Flow-level default configurations"""
    retry_logic: Optional[RetryLogic] = None
    
    def get_retry_config(self) -> RetryLogic:
        """Get retry logic with guaranteed defaults"""
        return self.retry_logic or RetryLogic()
    
    model_config = {"frozen": True}


# ============================================================================
# SHARED COMPONENT MODELS
# ============================================================================

class ValidationRule(BaseModel):
    """
    Validation rule for PROMPT nodes.
    
    Supports regex pattern matching or expression-based validation.
    """
    type: Literal["REGEX", "EXPRESSION"] = Field(
        ...,
        description="Type of validation to perform"
    )
    rule: str = Field(
        ...,
        min_length=1,
        description="Regex pattern or expression to evaluate"
    )
    error_message: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_ERROR_MESSAGE_LENGTH,
        description="Error message shown when validation fails"
    )
    
    @field_validator('rule')
    @classmethod
    def validate_rule_length(cls, v: str, info) -> str:
        """Validate rule length based on validation type"""
        val_type = info.data.get('type')
        
        if val_type == ValidationType.REGEX.value:
            if len(v) > SystemConstraints.MAX_REGEX_LENGTH:
                raise ValueError(
                    f"Regex pattern exceeds maximum length of {SystemConstraints.MAX_REGEX_LENGTH} characters"
                )
        elif val_type == ValidationType.EXPRESSION.value:
            if len(v) > SystemConstraints.MAX_EXPRESSION_LENGTH:
                raise ValueError(
                    f"Expression exceeds maximum length of {SystemConstraints.MAX_EXPRESSION_LENGTH} characters"
                )
        
        return v
    
    model_config = {"frozen": True, "extra": "forbid"}


class Interrupt(BaseModel):
    """
    Interrupt configuration for PROMPT and MENU nodes.
    
    Allows user to exit current flow by entering specific keywords.
    """
    input: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH,
        description="Keyword that triggers the interrupt"
    )
    target_node: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_NODE_ID_LENGTH,
        description="Node to redirect to when interrupt is triggered"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


class MenuStaticOption(BaseModel):
    """Static menu option for MENU nodes with source_type=STATIC"""
    label: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_OPTION_LABEL_LENGTH,
        description="Display text for the menu option"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


class MenuOutputMapping(BaseModel):
    """
    Output mapping for MENU nodes with source_type=DYNAMIC.

    Maps properties from selected item to flow variables.
    """
    source_path: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_SOURCE_PATH_LENGTH,
        description="JSON path to extract from selected item (e.g., 'id', 'user.name')"
    )
    target_variable: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_VARIABLE_NAME_LENGTH,
        description="Variable name to store extracted value"
    )

    @field_validator('target_variable')
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        """Ensure variable name follows identifier pattern and is not reserved"""
        if v in ReservedKeywords.RESERVED:
            raise ValueError(
                f"Variable name '{v}' is reserved. Reserved keywords: "
                f"{', '.join(ReservedKeywords.RESERVED)}"
            )
        if not re.match(RegexPatterns.IDENTIFIER, v):
            raise ValueError(
                f"Variable name '{v}' must start with a letter or underscore "
                f"and contain only letters, numbers, and underscores"
            )
        return v

    model_config = {"frozen": True, "extra": "forbid"}


class APIHeader(BaseModel):
    """
    HTTP header for API requests.
    
    Represents a single key-value header pair with validation.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_HEADER_NAME_LENGTH,
        description="Header name (e.g., 'Content-Type', 'Authorization')"
    )
    value: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_HEADER_VALUE_LENGTH,
        description="Header value (supports template variables)"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


class APIRequestConfig(BaseModel):
    """API request configuration for API_ACTION nodes"""
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        ...,
        description="HTTP method for the request"
    )
    url: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_REQUEST_URL_LENGTH,
        description="API endpoint URL (supports template variables)"
    )
    headers: Optional[List[APIHeader]] = Field(
        default=None,
        max_length=SystemConstraints.MAX_HEADERS_PER_REQUEST,
        description=f"HTTP headers (max {SystemConstraints.MAX_HEADERS_PER_REQUEST}, each supports template variables in value)"
    )
    body: Optional[str] = Field(
        default=None,
        description="Request body as JSON string for POST/PUT/PATCH (supports template variables)"
    )

    model_config = {"frozen": True, "extra": "forbid"}


class APIResponseMapping(BaseModel):
    """
    Response mapping for API_ACTION nodes.

    Maps data from API response to flow variables.
    """
    source_path: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_SOURCE_PATH_LENGTH,
        description="JSON path to extract from response (e.g., 'data.user.id')"
    )
    target_variable: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_VARIABLE_NAME_LENGTH,
        description="Variable name to store extracted value"
    )

    @field_validator('target_variable')
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        """Ensure variable name follows identifier pattern and is not reserved"""
        if v in ReservedKeywords.RESERVED:
            raise ValueError(
                f"Variable name '{v}' is reserved. Reserved keywords: "
                f"{', '.join(ReservedKeywords.RESERVED)}"
            )
        if not re.match(RegexPatterns.IDENTIFIER, v):
            raise ValueError(
                f"Variable name '{v}' must start with a letter or underscore "
                f"and contain only letters, numbers, and underscores"
            )
        return v

    model_config = {"frozen": True, "extra": "forbid"}


class APISuccessCheck(BaseModel):
    """
    Success check configuration for API_ACTION nodes.
    
    Determines whether API call succeeded based on status code or expression.
    """
    status_codes: Optional[List[int]] = Field(
        default=None,
        description="HTTP status codes considered successful (e.g., [200, 201])"
    )
    expression: Optional[str] = Field(
        default=None,
        max_length=SystemConstraints.MAX_EXPRESSION_LENGTH,
        description="Expression to evaluate success (e.g., 'response.status == \"ok\"')"
    )
    
    @model_validator(mode='after')
    def validate_at_least_one(self):
        """Ensure at least one success check method is specified"""
        if self.status_codes is None and self.expression is None:
            raise ValueError("At least one of 'status_codes' or 'expression' must be specified")
        return self
    
    model_config = {"frozen": True, "extra": "forbid"}


class APIResponse(BaseModel):
    """Wrapper for external API responses with validation"""
    status_code: int = Field(..., ge=100, le=599)
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Any  # Can be dict, list, string, etc.
    success: bool = False
    
    @classmethod
    def from_httpx_response(cls, response: "httpx.Response") -> "APIResponse":
        """
        Convert httpx.Response to typed APIResponse
        
        Args:
            response: httpx Response object
            
        Returns:
            APIResponse with validated structure
            
        Raises:
            ConstraintViolationError: If response body exceeds MAX_RESPONSE_BODY_SIZE
        """
        import httpx
        from app.utils.exceptions import ConstraintViolationError
        
        # Check response body size before parsing
        content_length = response.headers.get('content-length')
        actual_size = len(response.content)
        
        # Use Content-Length header if available, otherwise use actual content size
        size_to_check = int(content_length) if content_length else actual_size
        
        if size_to_check > SystemConstraints.MAX_RESPONSE_BODY_SIZE:
            size_mb = size_to_check / (1024 * 1024)
            max_mb = SystemConstraints.MAX_RESPONSE_BODY_SIZE / (1024 * 1024)
            raise ConstraintViolationError(
                f"API response body exceeds maximum size of {max_mb:.1f} MB (received: {size_mb:.2f} MB)",
                constraint="MAX_RESPONSE_BODY_SIZE"
            )
        
        # Try to parse JSON body, fallback to text
        try:
            body = response.json()
        except Exception:
            body = response.text
        
        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            success=response.is_success
        )
    
    def extract_value(self, path: str) -> Any:
        """
        Safely extract value from body using dot notation
        
        Args:
            path: Dot-separated path like "data.user.name" or "items[0].id"
            
        Returns:
            Extracted value or None if path not found
        """
        if not isinstance(self.body, dict):
            return None
        
        keys = path.split('.')
        current = self.body
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None
        
        return current
    
    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class Route(BaseModel):
    """
    Node routing configuration.
    
    Defines conditional transitions between nodes.
    """
    condition: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_ROUTE_CONDITION_LENGTH,
        description="Condition expression to evaluate (e.g., 'success', 'error', 'selection == 1')"
    )
    target_node: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_NODE_ID_LENGTH,
        description="Target node ID to transition to when condition is true"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


# ============================================================================
# NODE CONFIGURATION MODELS
# ============================================================================

class MessageNodeConfig(BaseModel):
    """
    Configuration for MESSAGE nodes.
    
    Sends a message to the user without waiting for input.
    """
    type: Literal["MESSAGE"] = Field(default="MESSAGE", frozen=True)
    text: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_MESSAGE_LENGTH,
        description="Message text to display (supports template variables)"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


class PromptNodeConfig(BaseModel):
    """
    Configuration for PROMPT nodes.
    
    Displays a message and waits for user input, storing it in a variable.
    """
    type: Literal["PROMPT"] = Field(default="PROMPT", frozen=True)
    text: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_MESSAGE_LENGTH,
        description="Prompt text to display (supports template variables)"
    )
    save_to_variable: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_VARIABLE_NAME_LENGTH,
        description="Variable name to store user input"
    )
    validation: Optional[ValidationRule] = Field(
        default=None,
        description="Optional validation rule for user input"
    )
    interrupts: Optional[List[Interrupt]] = Field(
        default=None,
        description="Optional interrupt keywords for flow exit"
    )
    
    @field_validator('save_to_variable')
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        """Ensure variable name follows identifier pattern and is not reserved"""
        if v in ReservedKeywords.RESERVED:
            raise ValueError(
                f"Variable name '{v}' is reserved. Reserved keywords: "
                f"{', '.join(ReservedKeywords.RESERVED)}"
            )
        if not re.match(RegexPatterns.IDENTIFIER, v):
            raise ValueError(
                f"Variable name '{v}' must start with a letter or underscore "
                f"and contain only letters, numbers, and underscores"
            )
        return v
    
    model_config = {"frozen": True, "extra": "forbid"}


class MenuNodeConfig(BaseModel):
    """
    Configuration for MENU nodes.
    
    Displays options for user selection, supporting static or dynamic menus.
    """
    type: Literal["MENU"] = Field(default="MENU", frozen=True)
    text: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_MESSAGE_LENGTH,
        description="Menu prompt text (supports template variables)"
    )
    source_type: Literal["STATIC", "DYNAMIC"] = Field(
        ...,
        description="Type of menu options source"
    )
    
    # Fields for STATIC menus
    static_options: Optional[List[MenuStaticOption]] = Field(
        default=None,
        description="Static menu options (required when source_type=STATIC)"
    )
    
    # Fields for DYNAMIC menus
    source_variable: Optional[str] = Field(
        default=None,
        max_length=SystemConstraints.MAX_VARIABLE_NAME_LENGTH,
        description="Variable containing array of items (required when source_type=DYNAMIC)"
    )
    item_template: Optional[str] = Field(
        default=None,
        max_length=SystemConstraints.MAX_OPTION_LABEL_LENGTH,
        description="Template for rendering each item (required when source_type=DYNAMIC)"
    )
    output_mapping: Optional[List[MenuOutputMapping]] = Field(
        default=None,
        description="Mappings to extract data from selected item (for DYNAMIC menus)"
    )
    
    # Optional fields
    error_message: Optional[str] = Field(
        default=None,
        max_length=SystemConstraints.MAX_ERROR_MESSAGE_LENGTH,
        description="Custom error message for invalid menu selection"
    )
    interrupts: Optional[List[Interrupt]] = Field(
        default=None,
        description="Optional interrupt keywords for flow exit"
    )
    
    @model_validator(mode='after')
    def validate_menu_configuration(self):
        """Validate menu configuration based on source_type"""
        if self.source_type == MenuSourceType.STATIC.value:
            # STATIC menu must have static_options
            if not self.static_options:
                raise ValueError("STATIC menu must have 'static_options'")

            # STATIC menu must have 1-8 options
            if len(self.static_options) < 1 or len(self.static_options) > SystemConstraints.MAX_STATIC_MENU_OPTIONS:
                raise ValueError(
                    f"STATIC menu must have between 1 and {SystemConstraints.MAX_STATIC_MENU_OPTIONS} options"
                )

        elif self.source_type == MenuSourceType.DYNAMIC.value:
            # DYNAMIC menu must have source_variable and item_template
            if not self.source_variable:
                raise ValueError("DYNAMIC menu must have 'source_variable'")
            if not self.item_template:
                raise ValueError("DYNAMIC menu must have 'item_template'")
            # Note: Dynamic menu runtime limit (24 options) enforced in processor by truncating source array

        return self
    
    model_config = {"frozen": True, "extra": "forbid"}


class APIActionNodeConfig(BaseModel):
    """
    Configuration for API_ACTION nodes.
    
    Makes HTTP API calls and processes responses.
    """
    type: Literal["API_ACTION"] = Field(default="API_ACTION", frozen=True)
    request: APIRequestConfig = Field(
        ...,
        description="API request configuration"
    )
    response_map: Optional[List[APIResponseMapping]] = Field(
        default=None,
        description="Mappings to extract data from response body"
    )
    output_mapping: Optional[List[APIResponseMapping]] = Field(
        default=None,
        description="Alternative name for response_map (deprecated, use response_map)"
    )
    success_check: Optional[APISuccessCheck] = Field(
        default=None,
        description="Configuration to determine API call success"
    )
    
    model_config = {"frozen": True, "extra": "forbid"}


class LogicExpressionNodeConfig(BaseModel):
    """
    Configuration for LOGIC_EXPRESSION nodes.

    Evaluates expressions for conditional branching without user interaction.
    All logic is defined in the node's routes array.
    """
    type: Literal["LOGIC_EXPRESSION"] = Field(default="LOGIC_EXPRESSION", frozen=True)

    model_config = {"frozen": True, "extra": "forbid"}


class EndNodeConfig(BaseModel):
    """
    Configuration for END nodes.
    
    Terminates the flow execution.
    """
    type: Literal["END"] = Field(default="END", frozen=True)
    
    model_config = {"frozen": True, "extra": "forbid"}


# ============================================================================
# DISCRIMINATED UNION
# ============================================================================

NodeConfig = Union[
    MessageNodeConfig,
    PromptNodeConfig,
    MenuNodeConfig,
    APIActionNodeConfig,
    LogicExpressionNodeConfig,
    EndNodeConfig
]


# ============================================================================
# FLOW NODE MODEL
# ============================================================================

class FlowNode(BaseModel):
    """
    Complete node definition with configuration and routing.
    
    This model represents a single node in a flow, including its
    configuration, type, and routing logic.
    """
    id: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_NODE_ID_LENGTH,
        description="Unique node identifier within the flow"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Human-readable node name"
    )
    type: Literal["MESSAGE", "PROMPT", "MENU", "API_ACTION", "LOGIC_EXPRESSION", "END"] = Field(
        ...,
        description="Node type"
    )
    config: NodeConfig = Field(
        ...,
        discriminator='type',
        description="Node-specific configuration"
    )
    routes: Optional[List[Route]] = Field(
        default=None,
        max_length=SystemConstraints.MAX_ROUTES_PER_NODE,
        description="Routing configuration (required for all nodes except END)"
    )
    position: Dict[str, float] = Field(
        ...,
        description="Node position on canvas (x, y coordinates)"
    )

    @field_validator('position')
    @classmethod
    def validate_position(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate that position has required x and y keys with numeric values"""
        if not isinstance(v, dict):
            raise ValueError("Position must be a dictionary")
        if 'x' not in v or 'y' not in v:
            raise ValueError("Position must have 'x' and 'y' keys")
        if not isinstance(v['x'], (int, float)) or not isinstance(v['y'], (int, float)):
            raise ValueError("Position x and y must be numeric values")
        return v

    @model_validator(mode='before')
    @classmethod
    def inject_type_into_config(cls, data: Any) -> Any:
        """Inject node type into config for discriminated union"""
        if isinstance(data, dict):
            # Get the node type
            node_type = data.get('type')
            config = data.get('config')
            
            # If config exists and doesn't have type, add it
            if config and isinstance(config, dict) and 'type' not in config:
                config['type'] = node_type
        
        return data
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace"""
        if not v.strip():
            raise ValueError("Node name cannot be empty or whitespace only")
        return v
    
    @model_validator(mode='after')
    def validate_routes_required(self):
        """Validate that routes are required for non-END nodes"""
        if self.type != NodeType.END.value:
            if not self.routes or len(self.routes) == 0:
                raise ValueError(f"{self.type} nodes must have at least one route")
        return self
    
    @model_validator(mode='after')
    def validate_config_type_matches(self):
        """Ensure config type matches node type"""
        if self.config.type != self.type:
            raise ValueError(
                f"Node type '{self.type}' does not match config type '{self.config.type}'"
            )
        return self
    
    model_config = {"frozen": True, "extra": "forbid"}


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Flow metadata models
    'VariableType',
    'VariableDefinition',
    'RetryLogic',
    'FlowDefaults',
    
    # Shared components
    'ValidationRule',
    'Interrupt',
    'MenuStaticOption',
    'MenuOutputMapping',
    'APIHeader',
    'APIRequestConfig',
    'APIResponseMapping',
    'APISuccessCheck',
    'APIResponse',
    'Route',
    
    # Node configs
    'MessageNodeConfig',
    'PromptNodeConfig',
    'MenuNodeConfig',
    'APIActionNodeConfig',
    'LogicExpressionNodeConfig',
    'EndNodeConfig',
    
    # Union and main model
    'NodeConfig',
    'FlowNode',
]