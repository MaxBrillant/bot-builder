"""
PROMPT Processor
Collects and validates user input, saves to context variables
"""

from typing import Optional, Dict, Any
from app.processors.base_processor import BaseProcessor, ProcessResult
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
    
    async def process(
        self,
        node: Dict[str, Any],
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process PROMPT node
        
        Args:
            node: PROMPT node definition
            context: Session context
            user_input: User's input (None on first call)
        
        Returns:
            ProcessResult with message and/or next node
        """
        config = node.get('config', {})
        
        # First call: display message and wait for input
        if user_input is None:
            text = self.template_engine.render(config.get('text', ''), context)
            return ProcessResult(
                message=text,
                needs_input=True,
                context=context
            )
        
        # Sanitize input (trim whitespace)
        user_input = self.sanitize_input(user_input)
        
        # Check interrupts first (bypasses validation)
        interrupts = config.get('interrupts', [])
        interrupt_target = self.check_interrupt(user_input, interrupts)
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
        validation = config.get('validation')
        
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
                    error_msg = validation.get('error_message', ErrorMessages.FIELD_REQUIRED)
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
                    error_msg = validation.get('error_message', ErrorMessages.VALIDATION_FAILED)
        
        # Handle validation failure with retry logic
        if validation_failed:
            if session and db:
                # Track validation attempts
                from app.core.session_manager import SessionManager
                session_mgr = SessionManager(db)
                new_attempt_count = await session_mgr.increment_validation_attempts(session.session_id)
                
                # Get retry logic from flow defaults
                flow_defaults = context.get('_flow_defaults', {})
                retry_logic = flow_defaults.get('retry_logic', {})
                max_attempts = retry_logic.get('max_attempts', 3)
                fail_route = retry_logic.get('fail_route')
                counter_text = retry_logic.get('counter_text', '')
                
                # Check if max attempts exceeded
                if new_attempt_count >= max_attempts:
                    # Max attempts reached
                    await session_mgr.reset_validation_attempts(session.session_id)
                    
                    if fail_route:
                        # Route to fail_route
                        self.logger.warning(
                            f"Max validation attempts reached, routing to fail_route",
                            attempts=new_attempt_count,
                            max_attempts=max_attempts,
                            fail_route=fail_route
                        )
                        return ProcessResult(
                            next_node=fail_route,
                            context=context
                        )
                    else:
                        # No fail_route defined, terminate session per spec
                        self.logger.warning(
                            f"Max validation attempts reached, terminating session (no fail_route)",
                            attempts=new_attempt_count,
                            max_attempts=max_attempts
                        )
                        await session_mgr.error_session(session.session_id)
                        return ProcessResult(
                            message=f"{error_msg}\n\nMaximum attempts exceeded.",
                            terminal=True,
                            context=context
                        )
                
                # Render counter text if defined
                if counter_text:
                    counter_context = {
                        **context,
                        'current_attempt': new_attempt_count,
                        'max_attempts': max_attempts
                    }
                    rendered_counter = self.template_engine.render(counter_text, counter_context)
                    error_msg = f"{error_msg}\n{rendered_counter}"
            
            return ProcessResult(
                message=error_msg,
                needs_input=True,
                context=context
            )
        
        # Validation passed - reset validation attempts
        if session and db:
            from app.core.session_manager import SessionManager
            session_mgr = SessionManager(db)
            await session_mgr.reset_validation_attempts(session.session_id)
        
        # Save to variable
        save_to_var = config.get('save_to_variable')
        if save_to_var:
            # Get variable type from flow variables definition
            var_type = self._get_variable_type(save_to_var, context)
            
            # Convert input to appropriate type
            try:
                converted_value = self.validation_system.convert_type(user_input, var_type)
                context[save_to_var] = converted_value
                
                self.logger.info(
                    f"Saved input to variable '{save_to_var}'",
                    variable=save_to_var,
                    type=var_type
                )
            except Exception as e:
                self.logger.error(f"Type conversion failed: {str(e)}")
                # If type conversion fails, treat as validation error
                error_msg = validation.get('error_message', f"Invalid input format") if validation else "Invalid input format"
                return ProcessResult(
                    message=error_msg,
                    needs_input=True,
                    context=context
                )
        
        # Evaluate routes
        routes = node.get('routes', [])
        next_node = self.evaluate_routes(routes, context)
        
        return ProcessResult(
            next_node=next_node,
            context=context
        )
    
    def _validate_input(
        self,
        input_value: str,
        validation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Validate user input
        
        Args:
            input_value: User's input
            validation: Validation configuration
            context: Session context
        
        Returns:
            True if validation passes, False otherwise
        """
        validation_type = validation.get('type')
        rule = validation.get('rule', '')
        
        try:
            if validation_type == ValidationType.REGEX.value:
                return self.validation_system.validate_regex(input_value, rule)
            
            elif validation_type == ValidationType.EXPRESSION.value:
                return self.validation_system.validate_expression(input_value, rule, context)
            
            else:
                self.logger.warning(f"Unknown validation type: {validation_type}")
                return True  # Unknown validation type, pass by default
        
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}", rule=rule)
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