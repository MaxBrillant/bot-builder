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

    Validation performed at flow creation time (per spec section 6):
    - REGEX: Checks for unsupported features (lookahead/lookbehind/named groups)
    - EXPRESSION: Checks for unsupported methods (only isAlpha/isNumeric/isDigit allowed)
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
    def validate_rule_syntax(cls, v: str, info) -> str:
        """
        Validate rule syntax and length based on validation type

        Per spec section 6, validates:
        - REGEX: No lookahead/lookbehind, no named groups, valid pattern
        - EXPRESSION: Only supported methods (isAlpha/isNumeric/isDigit), no unsupported functions
        """
        val_type = info.data.get('type')

        # Check length constraints
        if val_type == ValidationType.REGEX.value:
            if len(v) > SystemConstraints.MAX_REGEX_LENGTH:
                raise ValueError(
                    f"Regex pattern exceeds maximum length of {SystemConstraints.MAX_REGEX_LENGTH} characters"
                )

            # Validate regex syntax: check for unsupported features
            cls._validate_regex_syntax(v)

        elif val_type == ValidationType.EXPRESSION.value:
            if len(v) > SystemConstraints.MAX_EXPRESSION_LENGTH:
                raise ValueError(
                    f"Expression exceeds maximum length of {SystemConstraints.MAX_EXPRESSION_LENGTH} characters"
                )

            # Validate expression syntax: check for unsupported methods
            cls._validate_expression_syntax(v)

        return v

    @staticmethod
    def _validate_regex_syntax(pattern: str) -> None:
        """
        Validate regex pattern for unsupported features

        Per spec section 6:
        - ❌ No lookahead/lookbehind assertions
        - ❌ No named groups

        Raises:
            ValueError: If pattern contains unsupported features or invalid syntax
        """
        # Check for unsupported regex features
        unsupported_features = [
            (r'\(\?[=!]', 'lookahead assertions (?= or ?!)', 'Use simple patterns without lookahead'),
            (r'\(\?<[=!]', 'lookbehind assertions (?<= or ?<!)', 'Use simple patterns without lookbehind'),
            (r'\(\?P<\w+>', 'named groups (?P<name>...)', 'Use unnamed capturing groups'),
        ]

        for feature_pattern, feature_name, suggestion in unsupported_features:
            if re.search(feature_pattern, pattern):
                raise ValueError(
                    f"Unsupported regex feature: {feature_name}. "
                    f"Suggestion: {suggestion}"
                )

        # Validate that pattern compiles
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {str(e)}")

    @staticmethod
    def _validate_expression_syntax(expr: str) -> None:
        """
        Validate expression syntax for unsupported methods

        Per spec section 6, only these are supported:
        - input.isAlpha(), input.isNumeric(), input.isDigit()
        - input.length (property)
        - context.* (variable access)
        - Comparison operators (==, !=, >, <, >=, <=)
        - Logical operators (&&, ||)

        Unsupported:
        - Custom functions (parseInt, toUpperCase, includes, etc.)
        - String methods beyond isAlpha/isNumeric/isDigit
        - Array/object methods

        Raises:
            ValueError: If expression contains unsupported features
        """
        # Check for unsupported input methods (method calls with parentheses)
        input_methods = re.findall(r'input\.(\w+)\s*\(', expr)
        supported_input_methods = ['isAlpha', 'isNumeric', 'isDigit']

        for method in input_methods:
            if method not in supported_input_methods:
                raise ValueError(
                    f"Unsupported method: input.{method}(). "
                    f"Supported methods: {', '.join(['input.' + m + '()' for m in supported_input_methods])}. "
                    f"Methods like toUpperCase(), includes(), toLowerCase() are not supported."
                )

        # Check for unsupported input properties (beyond 'length')
        # Find all input.xxx references, then exclude methods to get only properties
        all_input_refs = re.findall(r'input\.(\w+)', expr)
        input_properties = [ref for ref in all_input_refs if ref not in input_methods]
        supported_properties = ['length']

        for prop in input_properties:
            if prop not in supported_properties:
                raise ValueError(
                    f"Unsupported property: input.{prop}. "
                    f"Only 'input.length' is supported as a property."
                )

        # Check for standalone functions (e.g., parseInt, toUpperCase)
        # Pattern: word followed by parentheses that's NOT input.method() or context.
        standalone_functions = re.findall(r'\b(\w+)\s*\([^)]*\)', expr)

        # Filter out supported methods and keywords
        allowed_in_functions = supported_input_methods + ['input', 'context']
        unsupported_functions = [
            f for f in standalone_functions
            if f not in allowed_in_functions
        ]

        if unsupported_functions:
            raise ValueError(
                f"Unsupported functions: {', '.join(unsupported_functions)}. "
                f"Only input.isAlpha(), input.isNumeric(), and input.isDigit() are supported. "
                f"Functions like parseInt(), toUpperCase(), includes() are not supported."
            )

    model_config = {"frozen": True, "extra": "forbid"}


class Interrupt(BaseModel):
    """
    Interrupt configuration for PROMPT and MENU nodes.

    Allows user to exit current flow by entering specific keywords.

    Spec Requirements (line 1732):
    - Empty string "" is NOT allowed as interrupt keyword
    - Whitespace-only strings are not allowed
    - Maximum length: 96 characters
    - Whitespace in keywords allowed: "go back", "cancel order"
    - Case-insensitive matching
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

    @field_validator('input')
    @classmethod
    def validate_not_whitespace_only(cls, v: str) -> str:
        """
        Ensure interrupt keyword is not empty or whitespace-only (spec line 1732)

        Empty string "" is explicitly not allowed as interrupt keyword.
        Whitespace-only strings are also rejected.
        """
        if not v or not v.strip():
            raise ValueError(
                "Interrupt keyword cannot be empty or whitespace-only. "
                "Empty string '' is not allowed as an interrupt keyword (spec line 1732)."
            )
        return v

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

    @field_validator('source_path')
    @classmethod
    def validate_source_path(cls, v: str) -> str:
        """Ensure source_path uses dot notation only (spec lines 865, 960)"""
        if '[' in v or ']' in v:
            raise ValueError(
                f"Bracket notation not supported in source_path. "
                f"Use dot notation instead (e.g., 'items.0.name' not 'items[0].name')"
            )
        return v

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

    Supports dict, array, and primitive root responses:
    - Dict root: Use "field", "data.nested"
    - Array root: Use "*" (entire array), "*.0" (first item), "*.0.field"
    - Primitive root: Use "*"
    """
    source_path: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_SOURCE_PATH_LENGTH,
        description="JSON path to extract from response (e.g., 'data.user.id', '*', '*.0.id')"
    )
    target_variable: str = Field(
        ...,
        min_length=1,
        max_length=SystemConstraints.MAX_VARIABLE_NAME_LENGTH,
        description="Variable name to store extracted value"
    )

    @field_validator('source_path')
    @classmethod
    def validate_source_path(cls, v: str) -> str:
        """
        Ensure source_path uses dot notation only (spec lines 865, 960)

        Supports:
        - Dict root: "field", "data.nested"
        - Array root: "*", "*.0", "*.0.field"
        - Primitive root: "*"
        """
        if '[' in v or ']' in v:
            raise ValueError(
                f"Bracket notation not supported in source_path. "
                f"Use dot notation instead (e.g., 'data.items.0.name' not 'data.items[0].name'). "
                f"For root arrays, use '*' prefix (e.g., '*.0.id')."
            )
        return v

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
        
        # Handle HTTP 204 No Content specially (spec line 1961)
        # Empty response routes to success if status matches, response_map skipped
        if response.status_code == 204:
            return cls(
                status_code=response.status_code,
                headers=dict(response.headers),
                body={},  # Empty body for 204
                success=True  # 204 is considered success
            )

        # Parse JSON body - spec requires JSON-only responses (line 1954)
        # Non-JSON responses should route to error condition
        try:
            body = response.json()
            # Success depends on HTTP status
            success = response.is_success
        except Exception:
            # JSON parsing failed - this is an error regardless of status code
            # Non-JSON responses route to error (spec line 1954)
            body = {"error": "Response is not valid JSON"}
            success = False  # Force error route

        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            success=success
        )
    
    def extract_value(self, path: str) -> Any:
        """
        Safely extract value from body using dot notation

        Args:
            path: Dot-separated path like "data.user.name", "items.0.id", or "*" for root

        Returns:
            Extracted value or None if path not found

        Path Syntax:
            - "*" - return entire root (any type)
            - "field" - dict field access (requires dict root)
            - "*.0" - array index access (requires array root)
            - "*.0.field" - nested access in root array
            - "data.items.0.id" - nested dict/array traversal
        """
        # Special case: "*" returns entire body
        if path == "*":
            return self.body

        # Check if path starts with "*." (root array/primitive access)
        if path.startswith("*."):
            # Root must be array or list for "*." prefix
            if not isinstance(self.body, (list, tuple)):
                return None  # Invalid: * prefix on non-array root

            # Remove "*." prefix and continue with array as current
            path = path[2:]  # "*.0.id" becomes "0.id"
            current = self.body
        else:
            # Normal path - starts with field name
            # Root should be dict for field access
            if not isinstance(self.body, dict):
                return None  # Invalid: field access on non-dict root

            current = self.body

        # Traverse path parts
        keys = path.split('.')
        for key in keys:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, (list, tuple)):
                try:
                    index = int(key)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None  # Index out of bounds
                except ValueError:
                    return None  # Non-numeric index on array
            else:
                return None  # Cannot traverse further

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
        max_length=SystemConstraints.MAX_TEMPLATE_LENGTH,
        description="Template for rendering each item (required when source_type=DYNAMIC, max 1024 chars per spec line 1637)"
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

            # STATIC menu cannot have output_mapping (spec line 858)
            if self.output_mapping is not None:
                raise ValueError("output_mapping only works with DYNAMIC source_type. Remove output_mapping from STATIC menu.")

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