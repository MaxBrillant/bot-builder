"""
API_ACTION Processor
Executes HTTP requests to external APIs
"""

from typing import Optional, Dict, Any, List
import httpx
import json

from app.utils.constants import HTTPMethod, SpecialVariables, VariableType, SystemConstraints
from app.utils.exceptions import ConstraintViolationError
from app.utils.security import is_safe_url_for_ssrf
from app.models.node_configs import (
    FlowNode,
    APIActionNodeConfig,
    APIHeader,
    APIResponseMapping,
    APIResponse
)
from app.models.audit_log import AuditResult
from app.repositories.audit_log_repository import AuditLogRepository
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
            # Skip response mapping for HTTP 204 No Content (spec line 1961)
            if api_response.status_code == 204:
                self.logger.info(
                    f"API call successful (204 No Content, response_map skipped)",
                    status_code=api_response.status_code
                )
            elif config.response_map:
                # Apply response mapping - failures preserve existing values and don't affect routing
                self._apply_response_mapping(api_response, config.response_map, context)
                self.logger.info(
                    f"API call successful",
                    status_code=api_response.status_code
                )
            else:
                self.logger.info(
                    f"API call successful",
                    status_code=api_response.status_code
                )

            context[SpecialVariables.API_RESULT] = 'success'
        else:
            context[SpecialVariables.API_RESULT] = 'error'
            self.logger.warning(
                f"API call failed success check",
                status_code=api_response.status_code
            )

        # Audit log: API call (without sensitive data)
        if db and session:
            audit_log = AuditLogRepository(db)
            # Get rendered URL for logging (strip query params for security)
            rendered_url = self.template_engine.render_url(config.request.url, context)
            # Extract base URL (without query string) for audit log
            base_url = rendered_url.split('?')[0] if '?' in rendered_url else rendered_url

            await audit_log.log_api_call(
                method=config.request.method.upper(),
                url=base_url,
                status_code=api_response.status_code,
                user_id=logger.mask_pii(session.channel_user_id, "user_id") if hasattr(session, 'channel_user_id') else None,
                result=AuditResult.SUCCESS if is_success else AuditResult.FAILED,
                event_metadata={
                    "session_id": str(session.session_id) if hasattr(session, 'session_id') else None,
                    "bot_id": str(session.bot_id) if hasattr(session, 'bot_id') else None,
                    "node_id": node.id,
                    "api_result": context.get(SpecialVariables.API_RESULT)
                }
            )

        # Check if node is terminal (has no routes)
        terminal = self.check_terminal(node, context)
        if terminal:
            return terminal

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

        # SECURITY: Enforce HTTPS for all API calls (Spec Section 10.6)
        # "Always use HTTPS for API endpoints" - BOT_BUILDER_SPECIFICATIONS.md
        if not rendered_url.startswith("https://"):
            self.logger.error(
                "API endpoint must use HTTPS",
                url=rendered_url,
                security_requirement="HTTPS_REQUIRED"
            )
            return APIResponse(
                status_code=400,
                body={"error": "API endpoints must use HTTPS. Insecure HTTP connections are not allowed."},
                success=False
            )

        # SECURITY: SSRF Protection - Block requests to private/internal networks
        is_safe, ssrf_error = is_safe_url_for_ssrf(rendered_url)
        if not is_safe:
            self.logger.error(
                "API endpoint blocked by SSRF protection",
                url=rendered_url,
                reason=ssrf_error,
                security_requirement="SSRF_PROTECTION"
            )
            return APIResponse(
                status_code=403,
                body={"error": "API endpoint not allowed: requests to internal or private networks are blocked."},
                success=False
            )

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
                body={"error": "Request or response payload too large"},
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
            self.logger.warning(f"API call request error: {str(e)}", url=rendered_url)
            return APIResponse(
                status_code=500,
                body={"error": "API request failed"},
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
        Render request body with context variables and type preservation

        Template variables in JSON bodies preserve their native types:
        - Numbers remain numbers (not converted to strings)
        - Booleans remain booleans
        - Arrays remain arrays
        - Strings remain strings

        Type is determined by:
        1. Flow variable type definition (if declared)
        2. Actual Python value type (if not declared)

        Args:
            body_json_string: Body as JSON string (with possible template variables)
            context: Session context

        Returns:
            Rendered body structure with proper types preserved

        Raises:
            ConstraintViolationError: If rendered body exceeds MAX_REQUEST_BODY_SIZE
        """
        # Parse JSON string to get structure
        try:
            body_template = json.loads(body_json_string)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse body JSON: {str(e)}")
            return {}

        # Get flow variables for type lookup
        flow_variables = context.get("_flow_variables", {})

        # Recursively render templates in the parsed structure with type preservation
        def render_structure(obj: Any) -> Any:
            if isinstance(obj, dict):
                rendered = {}
                for key, value in obj.items():
                    if isinstance(value, str):
                        # Use type-aware rendering for JSON values
                        rendered[key] = self.template_engine.render_json_value(
                            value, context, flow_variables
                        )
                    elif isinstance(value, (dict, list)):
                        rendered[key] = render_structure(value)
                    else:
                        rendered[key] = value
                return rendered
            elif isinstance(obj, list):
                return [render_structure(item) for item in obj]
            elif isinstance(obj, str):
                return self.template_engine.render_json_value(obj, context, flow_variables)
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

        Both status_codes and expression are evaluated on equal footing with AND logic:
        - If only status_codes provided: status must match
        - If only expression provided: expression must evaluate to True
        - If both provided: BOTH must pass (AND logic)

        Args:
            api_response: Validated APIResponse object
            success_check: Optional APISuccessCheck instance

        Returns:
            True if successful, False otherwise
        """
        if not success_check:
            # Default: check status code in 200-299 range
            return api_response.success

        # Evaluate each check that's provided (AND logic)
        status_check_passed = True
        expression_check_passed = True

        # Check status codes if provided
        if success_check.status_codes:
            status_check_passed = api_response.status_code in success_check.status_codes

        # Check expression if provided
        if success_check.expression:
            # Create context with response data
            eval_context = {
                'response': {
                    'body': api_response.body,
                    'status': api_response.status_code,
                    'headers': api_response.headers
                }
            }

            try:
                expression_check_passed = self.condition_evaluator.evaluate(
                    success_check.expression, eval_context
                )
            except Exception as e:
                self.logger.error(f"Success check expression error: {str(e)}")
                expression_check_passed = False

        # Both conditions must pass (AND logic)
        return status_check_passed and expression_check_passed
    
    def _apply_response_mapping(
        self,
        api_response: APIResponse,
        mappings: List[APIResponseMapping],
        context: Dict[str, Any]
    ) -> None:
        """
        Apply response mapping to extract data into context with type inference

        Args:
            api_response: Validated APIResponse object
            mappings: List of typed APIResponseMapping instances
            context: Session context (updated in place)

        Note:
            - Missing or null fields preserve existing value (default or previously set)
            - Type conversion failures preserve existing value
            - All mappings execute independently (no partial failures affect routing)
            - Type conversion based on variable's declared type
            - Supports dict, array, and primitive root responses:
              - Dict root: Use "field", "data.nested"
              - Array root: Use "*", "*.0", "*.0.field"
              - Primitive root: Use "*"

        Example:
            api_response.body = {"user": {"id": "123", "name": "Alice"}}
            mappings = [
                APIResponseMapping(source_path="user.id", target_variable="user_id"),
                APIResponseMapping(source_path="user.name", target_variable="user_name")
            ]

            With flow variables:
                {"user_id": {"type": "NUMBER"}, "user_name": {"type": "STRING"}}

            Result: context updated with user_id=123 (as number), user_name="Alice"
        """
        # Get variable definitions from flow for type inference
        variables = context.get("_flow_variables", {})

        for mapping in mappings:
            source_path = mapping.source_path
            target_var = mapping.target_variable

            if not target_var:
                continue

            # Check if variable exists in flow variables definition
            if target_var not in variables:
                # Skip mapping if variable doesn't exist in flow schema
                self.logger.warning(
                    f"API_ACTION node references non-existent variable, skipping mapping: {target_var}",
                    source_path=source_path,
                    target_variable=target_var
                )
                continue

            # Look up the target variable's declared type
            var_definition = variables.get(target_var, {})
            var_type = var_definition.get("type", "STRING")  # Default to string if not defined

            # Use safe extraction method
            value = api_response.extract_value(source_path)

            # Handle null values or missing paths - preserve existing value
            if value is None:
                self.logger.debug(
                    f"Response mapping: {source_path} -> {target_var} skipped (missing or null value, preserving existing)",
                    source=source_path,
                    target=target_var
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
                # On conversion failure, preserve existing value and continue with other mappings
                self.logger.warning(
                    f"Response mapping conversion failed for '{target_var}', preserving existing value: {str(e)}",
                    source=source_path,
                    target=target_var,
                    inferred_type=var_type,
                    value=value
                )
    