"""
API_ACTION Processor
Executes HTTP requests to external APIs
"""

from typing import Optional, Dict, Any, List
import httpx
import json

from app.utils.constants import HTTPMethod, SpecialVariables, VariableType, SystemConstraints
from app.utils.exceptions import ConstraintViolationError
from app.models.node_configs import (
    FlowNode,
    APIActionNodeConfig,
    APIHeader,
    APIResponseMapping,
    APIResponse
)
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger
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
    - Type conversion (string, number, boolean, array)
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
        node: FlowNode,
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process API_ACTION node
        
        Args:
            node: Typed FlowNode with API_ACTION configuration
            context: Session context
            user_input: Not used (API calls don't require user input)
        
        Returns:
            ProcessResult with success/error status
        """
        # Type narrow config for IDE support
        config: APIActionNodeConfig = node.config
        
        # Make request and get validated response
        api_response = await self._make_request(config, context)
        
        # Check success conditions
        is_success = self._check_success(api_response, config.success_check)
        
        if is_success:
            # Apply response mapping
            if config.response_map:
                mapping_success = self._apply_response_mapping(api_response, config.response_map, context)
                if not mapping_success:
                    self.logger.error("Response mapping failed due to conversion errors")
                    context[SpecialVariables.API_RESULT] = 'error'
                else:
                    context[SpecialVariables.API_RESULT] = 'success'
                    
                    self.logger.info(
                        f"API call successful",
                        status_code=api_response.status_code
                    )
            else:
                context[SpecialVariables.API_RESULT] = 'success'
                
                self.logger.info(
                    f"API call successful",
                    status_code=api_response.status_code
                )
        else:
            context[SpecialVariables.API_RESULT] = 'error'
            
            self.logger.warning(
                f"API call failed success check",
                status_code=api_response.status_code
            )
        
        # Evaluate routes based on success/error
        next_node = self.evaluate_routes(node.routes, context, node.type)
        
        return ProcessResult(
            next_node=next_node,
            context=context
        )
    
    async def _make_request(
        self,
        config: APIActionNodeConfig,
        context: Dict[str, Any]
    ) -> APIResponse:
        """Execute API request and return validated response"""
        
        # Render URL with context variables and URL encoding
        rendered_url = self.template_engine.render_url(config.request.url, context)
        
        # Get HTTP method
        method = config.request.method.upper()
        
        # Render headers (convert List[APIHeader] to Dict[str, str])
        headers_dict = self._render_headers(config.request.headers or [], context)
        
        # Render request body (for POST, PUT, PATCH)
        rendered_body = None
        if method in ['POST', 'PUT', 'PATCH']:
            if config.request.body:
                # Body is now a JSON string, parse and render it
                rendered_body = self._render_body(config.request.body, context)
        
        # Log API call (without sensitive data)
        self.logger.log_api_call(
            method=method,
            url=rendered_url,
            has_body=rendered_body is not None
        )
        
        try:
            response = await self.http_client.request(
                method=method,
                url=rendered_url,
                headers=headers_dict,
                json=rendered_body,
                timeout=settings.http_client.timeout
            )
            
            # Wrap external response in validated model
            return APIResponse.from_httpx_response(response)
            
        except ConstraintViolationError as e:
            # Handle size constraint violations (request or response body)
            self.logger.error(f"API size constraint violated: {e.message}", url=rendered_url)
            return APIResponse(
                status_code=413,  # Payload Too Large
                body={"error": e.message},
                success=False
            )
        except httpx.TimeoutException:
            # Return error response with proper structure
            self.logger.warning(f"API call timed out after {settings.http_client.timeout}s", url=rendered_url)
            return APIResponse(
                status_code=408,
                body={"error": "Request timeout"},
                success=False
            )
        except httpx.RequestError as e:
            self.logger.error(f"API call request error: {str(e)}", url=rendered_url)
            return APIResponse(
                status_code=500,
                body={"error": str(e)},
                success=False
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in API request: {e}", url=rendered_url)
            return APIResponse(
                status_code=500,
                body={"error": "Internal error"},
                success=False
            )
    
    def _render_headers(
        self,
        headers: List[APIHeader],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render header templates with context variables
        
        Args:
            headers: List of typed APIHeader instances
            context: Session context
        
        Returns:
            Rendered headers dictionary
        """
        rendered_headers = {}
        
        for header in headers:
            rendered_value = self.template_engine.render(header.value, context)
            rendered_headers[header.name] = rendered_value
        
        return rendered_headers
    
    def _render_body(
        self,
        body_json_string: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        Render request body with context variables
        
        Args:
            body_json_string: Body as JSON string (with possible template variables)
            context: Session context
        
        Returns:
            Rendered body structure (parsed from JSON)
            
        Raises:
            ConstraintViolationError: If rendered body exceeds MAX_REQUEST_BODY_SIZE
        """
        # Parse JSON string to get structure
        try:
            body_template = json.loads(body_json_string)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse body JSON: {str(e)}")
            return {}
        
        # Recursively render templates in the parsed structure
        def render_structure(obj: Any) -> Any:
            if isinstance(obj, dict):
                rendered = {}
                for key, value in obj.items():
                    if isinstance(value, str):
                        rendered[key] = self.template_engine.render(value, context)
                    elif isinstance(value, (dict, list)):
                        rendered[key] = render_structure(value)
                    else:
                        rendered[key] = value
                return rendered
            elif isinstance(obj, list):
                return [render_structure(item) for item in obj]
            elif isinstance(obj, str):
                return self.template_engine.render(obj, context)
            else:
                return obj
        
        rendered_body = render_structure(body_template)
        
        # Validate request body size after rendering
        # Serialize to JSON to get the actual size that will be sent
        try:
            body_json = json.dumps(rendered_body)
            body_size = len(body_json.encode('utf-8'))
            
            if body_size > SystemConstraints.MAX_REQUEST_BODY_SIZE:
                size_mb = body_size / (1024 * 1024)
                max_mb = SystemConstraints.MAX_REQUEST_BODY_SIZE / (1024 * 1024)
                self.logger.error(
                    f"Request body exceeds maximum size",
                    size_bytes=body_size,
                    max_bytes=SystemConstraints.MAX_REQUEST_BODY_SIZE
                )
                raise ConstraintViolationError(
                    f"Request body exceeds maximum size of {max_mb:.1f} MB (current: {body_size:,} bytes)",
                    constraint="MAX_REQUEST_BODY_SIZE"
                )
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to serialize request body for size check: {str(e)}")
            # If we can't serialize it, let httpx handle it downstream
            pass
        
        return rendered_body
    
    def _check_success(
        self,
        api_response: APIResponse,
        success_check: Optional[Any]
    ) -> bool:
        """
        Check if API call was successful
        
        Args:
            api_response: Validated APIResponse object
            success_check: Optional APISuccessCheck instance
        
        Returns:
            True if successful, False otherwise
        """
        if not success_check:
            # Default: check status code in 200-299 range
            return api_response.success
        
        # Check status code list
        status_codes = success_check.status_codes or []
        if status_codes and api_response.status_code in status_codes:
            return True
        
        # Check expression
        if success_check.expression:
            # Create context with response data
            eval_context = {
                'response': {
                    'body': api_response.body,
                    'status': api_response.status_code
                }
            }
            
            try:
                return self.condition_evaluator.evaluate(success_check.expression, eval_context)
            except Exception as e:
                self.logger.error(f"Success check expression error: {str(e)}")
                return False
        
        return False
    
    def _apply_response_mapping(
        self,
        api_response: APIResponse,
        mappings: List[APIResponseMapping],
        context: Dict[str, Any]
    ) -> bool:
        """
        Apply response mapping to extract data into context with type inference
        
        Args:
            api_response: Validated APIResponse object
            mappings: List of typed APIResponseMapping instances
            context: Session context (updated in place)
        
        Returns:
            bool: Always returns True (all mappings execute independently)
        
        Example:
            api_response.body = {"user": {"id": "123", "name": "Alice"}}
            mappings = [
                APIResponseMapping(source_path="user.id", target_variable="user_id"),
                APIResponseMapping(source_path="user.name", target_variable="user_name")
            ]
            
            With flow variables:
                {"user_id": {"type": "number"}, "user_name": {"type": "string"}}

            Result: context updated with user_id=123 (as number), user_name="Alice"
        """
        if not isinstance(api_response.body, dict):
            self.logger.warning(f"API response body is not a dict, cannot map: {type(api_response.body)}")
            return False
        
        # Get variable definitions from flow for type inference
        variables = context.get("_flow_variables", {})
        
        for mapping in mappings:
            source_path = mapping.source_path
            target_var = mapping.target_variable
            
            if not target_var:
                continue
            
            # Look up the target variable's declared type
            var_definition = variables.get(target_var, {})
            var_type = var_definition.get("type", "string")  # Default to string if not defined
            
            # Use safe extraction method
            value = api_response.extract_value(source_path)
            
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
            # Pass value directly without stringification - convert_type handles all types
            try:
                converted_value = self.validation_system.convert_type(value, var_type)

                self.logger.debug(
                    f"Response mapping: {source_path} -> {target_var}",
                    source=source_path,
                    target=target_var,
                    inferred_type=var_type,
                    original_type=type(value).__name__,
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
    