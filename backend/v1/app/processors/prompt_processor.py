"""
PROMPT Processor
Collects and validates user input, saves to context variables
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, PromptNodeConfig, ValidationRule
from app.models.audit_log import AuditResult
from app.repositories.audit_log_repository import AuditLogRepository
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.processors.retry_handler import RetryHandler
from app.utils.constants import ValidationType, ErrorMessages
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptProcessor(BaseProcessor):
    """
    Process PROMPT nodes - collect and validate user input

    Features:
    - Display message to user
    - Wait for input
    - Check interrupts (bypasses validation)
    - Validate input (REGEX or EXPRESSION)
    - Handle empty input (rejected by default unless validation allows)
    - Type conversion on save
    - Retry tracking
    - Route to fail_route after max attempts

    Processing Order:
    1. Display message (first call, no user_input)
    2. Check interrupts (if matched, bypass all validation)
    3. Check empty input (rejected unless validation explicitly allows)
    4. Run validation (if defined)
    5. Convert type based on variable definition
    6. Save to variable
    7. Evaluate routes
    """

    def __init__(
        self,
        template_engine,
        condition_evaluator,
        validation_system
    ):
        """Initialize with dependencies including retry handler"""
        super().__init__(template_engine, condition_evaluator, validation_system)
        # Create retry handler with shared dependencies
        # Note: SessionManager will be passed from process() context
        self.retry_handler = None  # Initialized lazily in process()

    async def process(
        self,
        node: FlowNode,
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process PROMPT node
        
        Args:
            node: Typed FlowNode with PROMPT configuration
            context: Session context
            user_input: User's input (None on first call)
        
        Returns:
            ProcessResult with message and/or next node
        """
        # Type narrow config for IDE support
        config: PromptNodeConfig = node.config
        
        # First call: display message and wait for input
        if user_input is None:
            try:
                text = self.template_engine.render(config.text, context)
            except Exception as e:
                self.logger.error(
                    f"Template rendering error in PROMPT node '{node.id}': {str(e)}",
                    node_id=node.id,
                    error=str(e)
                )
                # Fallback to unrendered text to avoid flow crash
                text = f"Error rendering prompt: {config.text[:100]}..."
            return ProcessResult(
                message=text,
                needs_input=True,
                context=context
            )
        
        # Sanitize input (trim whitespace)
        user_input = self.sanitize_input(user_input)
        
        # Check interrupts first (bypasses validation)
        interrupt_target = self.check_interrupt(user_input, config.interrupts or [])
        if interrupt_target:
            self.logger.info(f"Interrupt triggered to {interrupt_target}")
            # Reset validation attempts on interrupt
            if session and db:
                from app.core.session_manager import SessionManager
                session_mgr = SessionManager(db)
                await session_mgr.reset_validation_attempts(session.session_id)
            return ProcessResult(
                next_node=interrupt_target,
                context=context
            )
        
        # Get validation configuration
        validation = config.validation
        
        # Perform validation
        validation_failed = False
        error_msg = None
        
        # Handle empty input
        if len(user_input) == 0:
            if validation:
                # Let validation handle empty input
                is_valid = self._validate_input(user_input, validation, context)
                if not is_valid:
                    validation_failed = True
                    error_msg = validation.error_message
                    # Render template if it contains variables (with error handling)
                    try:
                        error_msg = self.template_engine.render(error_msg, context)
                    except Exception as e:
                        self.logger.error(
                            f"Template rendering error for validation error message: {str(e)}",
                            node_id=node.id
                        )
                        # Use unrendered message as fallback
                        pass
            else:
                # No validation defined, empty input rejected by default
                validation_failed = True
                error_msg = ErrorMessages.FIELD_REQUIRED
        else:
            # Non-empty input: validate if validation defined
            if validation:
                is_valid = self._validate_input(user_input, validation, context)
                if not is_valid:
                    validation_failed = True
                    error_msg = validation.error_message
                    # Render template if it contains variables (with error handling)
                    try:
                        error_msg = self.template_engine.render(error_msg, context)
                    except Exception as e:
                        self.logger.error(
                            f"Template rendering error for validation error message: {str(e)}",
                            node_id=node.id
                        )
                        # Use unrendered message as fallback
                        pass
        
        # Handle validation failure with retry logic
        if validation_failed:
            if session and db:
                # Initialize retry handler with session manager
                from app.core.session_manager import SessionManager
                session_mgr = SessionManager(db)
                retry_handler = RetryHandler(session_mgr, self.template_engine)

                # Audit log: validation failure
                audit_log = AuditLogRepository(db)
                await audit_log.log_validation_failure(
                    node_id=node.id,
                    attempt=session.validation_attempts + 1,
                    user_id=logger.mask_pii(session.channel_user_id, "user_id"),
                    event_metadata={
                        "session_id": str(session.session_id),
                        "bot_id": str(session.bot_id),
                        "validation_type": validation.type if validation else "default_required"
                    }
                )

                # Handle validation failure
                retry_result = await retry_handler.handle_validation_failure(
                    session,
                    context,
                    error_msg
                )

                # Check if should continue with retry
                if retry_result.should_continue:
                    return ProcessResult(
                        message=retry_result.error_message,
                        needs_input=True,
                        context=context
                    )

                # Max attempts reached - route or terminate
                if retry_result.terminal:
                    return ProcessResult(
                        message=retry_result.error_message,
                        terminal=True,
                        status=retry_result.status,
                        context=context
                    )

                # Route to fail_route
                return ProcessResult(
                    next_node=retry_result.next_node,
                    context=context
                )

            # No session/db - just return error
            return ProcessResult(
                message=error_msg,
                needs_input=True,
                context=context
            )

        # Save to variable
        if config.save_to_variable:
            # Check if variable exists in flow variables definition
            flow_variables = context.get('_flow_variables', {})
            if config.save_to_variable not in flow_variables:
                # Skip saving if variable doesn't exist in flow schema
                # This will cause templates to display literal {{context.variable}} text
                self.logger.warning(
                    f"PROMPT node references non-existent variable, skipping save: {config.save_to_variable}",
                    node_id=node.id,
                    variable=config.save_to_variable
                )
                # Continue to route evaluation without saving
            else:
                # Get variable type from flow variables definition
                var_type = self._get_variable_type(config.save_to_variable, context)

                # Convert input to appropriate type
                try:
                    converted_value = self.validation_system.convert_type(user_input, var_type)
                    context[config.save_to_variable] = converted_value

                    self.logger.info(
                        f"Saved input to variable '{config.save_to_variable}'",
                        variable=config.save_to_variable,
                        type=var_type
                    )

                    # Validation and type conversion both passed - reset validation attempts
                    if session and db:
                        from app.core.session_manager import SessionManager
                        session_mgr = SessionManager(db)
                        retry_handler = RetryHandler(session_mgr, self.template_engine)
                        await retry_handler.reset_attempts(session)
                except Exception as e:
                    self.logger.error(f"Type conversion failed: {str(e)}")
                    # If type conversion fails, treat as validation error
                    error_msg = validation.error_message if validation else "Invalid input format"

                    # Handle type conversion failure with retry logic (counts toward max attempts)
                    if session and db:
                        from app.core.session_manager import SessionManager
                        session_mgr = SessionManager(db)
                        retry_handler = RetryHandler(session_mgr, self.template_engine)

                        # Audit log: type conversion failure (counted as validation failure)
                        audit_log = AuditLogRepository(db)
                        await audit_log.log_validation_failure(
                            node_id=node.id,
                            attempt=session.validation_attempts + 1,
                            user_id=logger.mask_pii(session.channel_user_id, "user_id"),
                            event_metadata={
                                "session_id": str(session.session_id),
                                "bot_id": str(session.bot_id),
                                "validation_type": "type_conversion",
                                "target_type": var_type,
                                "error": str(e)
                            }
                        )

                        # Handle type conversion failure through retry handler
                        retry_result = await retry_handler.handle_validation_failure(
                            session,
                            context,
                            error_msg
                        )

                        # Check if should continue with retry
                        if retry_result.should_continue:
                            return ProcessResult(
                                message=retry_result.error_message,
                                needs_input=True,
                                context=context
                            )

                        # Max attempts reached - route or terminate
                        if retry_result.terminal:
                            return ProcessResult(
                                message=retry_result.error_message,
                                terminal=True,
                                status=retry_result.status,
                                context=context
                            )

                        # Route to fail_route
                        return ProcessResult(
                            next_node=retry_result.next_node,
                            context=context
                        )

                    # No session/db - just return error
                    return ProcessResult(
                        message=error_msg,
                        needs_input=True,
                        context=context
                    )
        
        # Check if node has routes
        has_routes = node.routes and len(node.routes) > 0

        if not has_routes:
            # No routes = terminal node
            self.logger.debug(
                f"PROMPT node '{node.id}' has no routes - terminal node",
                node_id=node.id
            )
            return ProcessResult(
                next_node=None,
                context=context
            )

        # Evaluate routes for next node
        next_node = self.evaluate_routes(node.routes, context, node.type)

        return ProcessResult(
            next_node=next_node,
            context=context
        )
    
    def _validate_input(
        self,
        input_value: str,
        validation: ValidationRule,
        context: Dict[str, Any]
    ) -> bool:
        """
        Validate user input
        
        Args:
            input_value: User's input
            validation: Typed ValidationRule instance
            context: Session context
        
        Returns:
            True if validation passes, False otherwise
        """
        try:
            if validation.type == ValidationType.REGEX.value:
                # Render template variables in regex pattern
                rendered_rule = self.template_engine.render(validation.rule, context)
                return self.validation_system.validate_regex(input_value, rendered_rule)
            
            elif validation.type == ValidationType.EXPRESSION.value:
                return self.validation_system.validate_expression(input_value, validation.rule, context)
            
            else:
                self.logger.warning(f"Unknown validation type: {validation.type}")
                return True  # Unknown validation type, pass by default
        
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}", rule=validation.rule)
            return False
    
    def _get_variable_type(self, var_name: str, context: Dict[str, Any]) -> str:
        """
        Get variable type from flow variables definition
        
        Args:
            var_name: Variable name
            context: Session context (should contain _flow_variables if defined)
        
        Returns:
            Variable type string (default: 'string')
        """
        # Check if flow variables definition is in context
        flow_variables = context.get('_flow_variables', {})
        
        if var_name in flow_variables:
            var_def = flow_variables[var_name]
            if isinstance(var_def, dict):
                return var_def.get('type', 'string')
        
        # Default to string type
        return 'string'