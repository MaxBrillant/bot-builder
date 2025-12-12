"""
API_ACTION Processor
Executes HTTP requests to external APIs
"""

from typing import Optional, Dict, Any, List
import httpx
import json

from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger
from app.utils.constants import HTTPMethod, SpecialVariables, VariableType
from app.config import settings

logger = get_logger(__name__)


class APIActionProcessor(BaseProcessor):
    """
    Process API_ACTION nodes - execute external HTTP requests
    
    Features:
    - HTTP methods: GET, POST, PUT, DELETE, PATCH
    - Template-based URL and body
    - Custom headers
    - 30-second fixed timeout
    - JSON-only responses
    - Response data extraction with path notation
    - Type conversion (string, integer, boolean, array)
    - Success/failure routing
    - Server-side credential injection
    
    Constraints:
    - Fixed 30-second timeout (not configurable)
    - JSON responses only (non-JSON routes to error)
    - Response body size limit: 1 MB
    - Timeout triggers error route
    """
    
    def __init__(self, *args, http_client: Optional[httpx.AsyncClient] = None, **kwargs):
        """
        Initialize API Action processor
        
        Args:
            http_client: Optional HTTP client (will be set lazily to shared client)
            *args, **kwargs: Passed to BaseProcessor
        """
        super().__init__(*args, **kwargs)
        # Don't create client here - use shared one from conversation_engine
        self.http_client = http_client
    
    async def process(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process API_ACTION node
        
        Args:
            node: API_ACTION node definition
            context: Session context
            user_input: Not used (API calls don't require user input)
        
        Returns:
            ProcessResult with success/error status
        """
        config = node.get('config', {})
        request_config = config.get('request', {})
        
        # Render URL with context variables and URL encoding
        url_template = request_config.get('url', '')
        url = self.template_engine.render_url(url_template, context)
        
        # Get HTTP method
        method = request_config.get('method', 'GET').upper()
        
        # Render headers
        headers_template = request_config.get('headers', {})
        headers = self._render_headers(headers_template, context)
        
        # Render request body (for POST, PUT, PATCH)
        body = None
        if method in ['POST', 'PUT', 'PATCH']:
            body_template = request_config.get('body')
            if body_template:
                body = self._render_body(body_template, context)
        
        # Log API call (without sensitive data)
        self.logger.log_api_call(
            method=method,
            url=url,
            has_body=body is not None
        )
        
        try:
            # Make HTTP request with fixed 30-second timeout
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=settings.API_TIMEOUT
            )
            
            # Parse JSON response
            response_data = {}
            if response.content:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    # Non-JSON response, route to error
                    self.logger.warning(
                        f"Non-JSON response from API",
                        status_code=response.status_code,
                        content_type=response.headers.get('content-type')
                    )
                    context[SpecialVariables.API_RESULT] = 'error'
                    next_node = self.evaluate_routes(node.get('routes', []), context, node.get('type'))
                    return ProcessResult(next_node=next_node, context=context)
            
            # Check success conditions
            success_check = config.get('success_check', {})
            is_success = self._check_success(
                response.status_code,
                response_data,
                success_check
            )
            
            if is_success:
                # Apply response mapping
                response_map = config.get('response_map', [])
                if response_map:
                    mapping_success = self._apply_response_mapping(response_data, response_map, context)
                    if not mapping_success:
                        self.logger.error("Response mapping failed due to conversion errors")
                        context[SpecialVariables.API_RESULT] = 'error'
                    else:
                        context[SpecialVariables.API_RESULT] = 'success'
                        
                        self.logger.info(
                            f"API call successful",
                            status_code=response.status_code,
                            url=url
                        )
                else:
                    context[SpecialVariables.API_RESULT] = 'success'
                    
                    self.logger.info(
                        f"API call successful",
                        status_code=response.status_code,
                        url=url
                    )
            else:
                context[SpecialVariables.API_RESULT] = 'error'
                
                self.logger.warning(
                    f"API call failed success check",
                    status_code=response.status_code,
                    url=url
                )
        
        except httpx.TimeoutException:
            self.logger.warning(f"API call timed out after {settings.API_TIMEOUT}s", url=url)
            context[SpecialVariables.API_RESULT] = 'error'
        
        except httpx.RequestError as e:
            self.logger.error(f"API call request error: {str(e)}", url=url)
            context[SpecialVariables.API_RESULT] = 'error'
        
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}", url=url)
            context[SpecialVariables.API_RESULT] = 'error'
        
        # Evaluate routes based on success/error
        routes = node.get('routes', [])
        next_node = self.evaluate_routes(routes, context, node.get('type'))
        
        return ProcessResult(
            next_node=next_node,
            context=context
        )
    
    def _render_headers(
        self,
        headers_template: Dict[str, str],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render header templates with context variables
        
        Args:
            headers_template: Headers with template variables
            context: Session context
        
        Returns:
            Rendered headers dictionary
        """
        rendered_headers = {}
        
        for key, value_template in headers_template.items():
            rendered_value = self.template_engine.render(str(value_template), context)
            rendered_headers[key] = rendered_value
        
        return rendered_headers
    
    def _render_body(
        self,
        body_template: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Render request body with context variables
        
        Args:
            body_template: Body template (dict, list, or string)
            context: Session context
        
        Returns:
            Rendered body structure
        """
        if isinstance(body_template, dict):
            rendered = {}
            for key, value in body_template.items():
                if isinstance(value, str):
                    rendered[key] = self.template_engine.render(value, context)
                elif isinstance(value, (dict, list)):
                    rendered[key] = self._render_body(value, context)
                else:
                    rendered[key] = value
            return rendered
        
        elif isinstance(body_template, list):
            return [self._render_body(item, context) for item in body_template]
        
        elif isinstance(body_template, str):
            return self.template_engine.render(body_template, context)
        
        else:
            return body_template
    
    def _check_success(
        self,
        status_code: int,
        response_data: Dict[str, Any],
        success_check: Dict[str, Any]
    ) -> bool:
        """
        Check if API call was successful
        
        Args:
            status_code: HTTP status code
            response_data: Parsed JSON response
            success_check: Success check configuration
        
        Returns:
            True if successful, False otherwise
        """
        # Check status code
        valid_status_codes = success_check.get('status_code_in', [200, 201])
        if status_code not in valid_status_codes:
            return False
        
        # Check optional expression
        expression = success_check.get('expression')
        if expression:
            # Create context with response data
            eval_context = {
                'response': {
                    'body': response_data,
                    'status': status_code
                }
            }
            
            try:
                return self.condition_evaluator.evaluate(expression, eval_context)
            except Exception as e:
                self.logger.error(f"Success check expression error: {str(e)}")
                return False
        
        return True
    
    def _apply_response_mapping(
        self,
        response_data: Dict[str, Any],
        mappings: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """
        Apply response mapping to extract data into context with type inference
        
        Args:
            response_data: Parsed JSON response
            mappings: List of mapping definitions
            context: Session context (updated in place)
        
        Returns:
            bool: Always returns True (all mappings execute independently)
        
        Example:
            response_data = {"user": {"id": "123", "name": "Alice"}}
            mappings = [
                {"source_path": "user.id", "target_variable": "user_id"},
                {"source_path": "user.name", "target_variable": "user_name"}
            ]
            
            With flow variables:
                {"user_id": {"type": "integer"}, "user_name": {"type": "string"}}
            
            Result: context updated with user_id=123 (as integer), user_name="Alice"
        """
        # Get variable definitions from flow for type inference
        variables = context.get("_flow_variables", {})
        
        for mapping in mappings:
            source_path = mapping.get('source_path', '')
            target_var = mapping.get('target_variable', '')
            
            if not target_var:
                continue
            
            # Look up the target variable's declared type
            var_definition = variables.get(target_var, {})
            var_type = var_definition.get("type", "string")  # Default to string if not defined
            
            # Extract value from response
            value = self.get_nested_value(response_data, source_path)
            
            # Handle null values or missing paths - set to null
            if value is None:
                context[target_var] = None
                self.logger.debug(
                    f"Response mapping: {source_path} -> {target_var} = null (missing or null value)",
                    source=source_path,
                    target=target_var,
                    inferred_type=var_type
                )
                continue
            
            # Attempt type conversion based on variable's declared type
            try:
                # Special handling for arrays: if value is already a list and target is array,
                # use it directly without stringification to prevent comma-splitting bug
                if var_type == VariableType.ARRAY.value and isinstance(value, list):
                    converted_value = value
                    self.logger.debug(
                        f"Response mapping: {source_path} -> {target_var} (array passthrough)",
                        source=source_path,
                        target=target_var,
                        inferred_type=var_type,
                        value_type=type(value).__name__,
                        array_length=len(value)
                    )
                else:
                    converted_value = self.validation_system.convert_type(str(value), var_type)
                    self.logger.debug(
                        f"Response mapping: {source_path} -> {target_var}",
                        source=source_path,
                        target=target_var,
                        inferred_type=var_type,
                        value_type=type(value).__name__,
                        converted_type=type(converted_value).__name__
                    )
                
                context[target_var] = converted_value
            except Exception as e:
                # On conversion failure, set to null and continue with other mappings
                context[target_var] = None
                self.logger.warning(
                    f"Response mapping conversion failed for '{target_var}', setting to null: {str(e)}",
                    source=source_path,
                    target=target_var,
                    inferred_type=var_type,
                    value=value
                )
        
        # All mappings execute independently - always return success
        return True
    