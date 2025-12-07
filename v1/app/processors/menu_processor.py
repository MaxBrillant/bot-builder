"""
MENU Processor
Presents options (static or dynamic) and captures user selection
"""

from typing import Optional, Dict, Any, List
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.constants import MenuSourceType, ErrorMessages, SpecialVariables
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MenuProcessor(BaseProcessor):
    """
    Process MENU nodes - present options and capture selection
    
    Features:
    - Static options (hardcoded list)
    - Dynamic options (from context arrays)
    - Template-based option formatting
    - Numeric selection (1, 2, 3...)
    - Output mapping (dynamic only)
    - Interrupt support (checked before validation)
    - Invalid selection handling with retry
    
    Processing Order:
    1. Build options (static or dynamic)
    2. Display menu (first call)
    3. Check interrupts
    4. Validate selection (numeric, in range)
    5. Save selection as integer
    6. Apply output mapping (dynamic only)
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
        Process MENU node
        
        Args:
            node: MENU node definition
            context: Session context
            user_input: User's input (None on first call)
        
        Returns:
            ProcessResult with menu or next node
        """
        config = node.get('config', {})
        source_type = config.get('source_type')
        
        # Build options based on source type
        if source_type == MenuSourceType.STATIC.value:
            options = config.get('static_options', [])
        elif source_type == MenuSourceType.DYNAMIC.value:
            source_var = config.get('source_variable')
            source_array = context.get(source_var, [])
            item_template = config.get('item_template', '')
            options = self._render_dynamic_options(source_array, item_template, context)
        else:
            self.logger.error(f"Invalid source_type: {source_type}")
            return ProcessResult(
                message="Configuration error. Please contact support.",
                next_node=None,
                context=context
            )
        
        # First call: display menu
        if user_input is None:
            menu_text = self._format_menu(config.get('text', ''), options, context)
            return ProcessResult(
                message=menu_text,
                needs_input=True,
                context=context
            )
        
        # Sanitize input
        user_input = self.sanitize_input(user_input)
        
        # Check interrupts first
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
        
        # Validate selection (must be numeric and in range)
        validation_failed = False
        try:
            selection = int(user_input)
            if selection < 1 or selection > len(options):
                raise ValueError("Selection out of range")
        except ValueError:
            validation_failed = True
        
        # Handle validation failure with retry logic
        if validation_failed:
            error_msg = config.get('error_message', ErrorMessages.INVALID_SELECTION)
            
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
            
            # Re-display menu with error
            menu_text = self._format_menu(config.get('text', ''), options, context)
            full_message = f"{error_msg}\n\n{menu_text}"
            return ProcessResult(
                message=full_message,
                needs_input=True,
                context=context
            )
        
        # Validation passed - reset validation attempts
        if session and db:
            from app.core.session_manager import SessionManager
            session_mgr = SessionManager(db)
            await session_mgr.reset_validation_attempts(session.session_id)
        
        # Save selection (as integer, 1-based index)
        # Selection variable is INTEGER type for numeric comparisons
        context[SpecialVariables.SELECTION] = selection
        
        self.logger.info(f"Menu selection: {selection}", selection=selection)
        
        # Apply output mapping (dynamic menus only)
        if source_type == MenuSourceType.DYNAMIC.value:
            source_var = config.get('source_variable')
            source_array = context.get(source_var, [])
            output_mapping = config.get('output_mapping', [])
            
            if output_mapping and source_array:
                # Get selected item (0-based index)
                selected_index = selection - 1
                if 0 <= selected_index < len(source_array):
                    selected_item = source_array[selected_index]
                    self._apply_output_mapping(selected_item, output_mapping, context)
        
        # Evaluate routes
        routes = node.get('routes', [])
        next_node = self.evaluate_routes(routes, context)
        
        return ProcessResult(
            next_node=next_node,
            context=context
        )
    
    def _render_dynamic_options(
        self,
        items: List[Any],
        template: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Render dynamic options from array using template
        
        Args:
            items: Source array
            template: Item template with {{item.*}} and {{index}}
            context: Session context
        
        Returns:
            List of rendered option strings
        
        Example:
            items = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
            template = "{{index}}. {{item.name}} ({{item.age}})"
            Result: ["1. Alice (25)", "2. Bob (30)"]
        """
        options = []
        
        for index, item in enumerate(items, start=1):
            # Create template context with item and index
            template_context = {
                'item': item,
                'index': index,
                **context  # Include session context for additional variables
            }
            
            try:
                rendered = self.template_engine.render(template, template_context)
                options.append(rendered)
            except Exception as e:
                self.logger.error(f"Error rendering option {index}: {str(e)}")
                options.append(f"{index}. [Error rendering option]")
        
        return options
    
    def _format_menu(
        self,
        text: str,
        options: List[Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Format menu with header text and numbered options
        
        Args:
            text: Menu header text (supports templates)
            options: List of options (strings or dicts with 'label')
            context: Session context
        
        Returns:
            Formatted menu text
        
        Example:
            text = "Select an option:"
            options = ["Option A", "Option B"]
            Result:
            "Select an option:
            1. Option A
            2. Option B"
        """
        # Render header text
        header = self.template_engine.render(text, context)
        
        # Build option list
        option_lines = []
        for i, option in enumerate(options, start=1):
            # Handle option format (string or dict with 'label')
            if isinstance(option, dict):
                label = option.get('label', str(option))
            else:
                label = str(option)
            
            option_lines.append(f"{i}. {label}")
        
        # Combine header and options
        if option_lines:
            menu_text = f"{header}\n\n" + "\n".join(option_lines)
        else:
            menu_text = f"{header}\n\n[No options available]"
        
        return menu_text
    
    def _apply_output_mapping(
        self,
        selected_item: Any,
        mappings: List[Dict[str, str]],
        context: Dict[str, Any]
    ):
        """
        Apply output mapping to extract fields from selected item
        
        Args:
            selected_item: The selected item object
            mappings: List of mapping definitions
            context: Session context (updated in place)
        
        Note:
            - Missing or null fields are set to null (graceful handling)
            - All mappings execute (no partial failures)
        
        Example:
            selected_item = {"id": "123", "name": "Alice"}
            mappings = [
                {"source_path": "id", "target_variable": "user_id"},
                {"source_path": "name", "target_variable": "user_name"}
            ]
            Result: context updated with user_id="123", user_name="Alice"
        """
        for mapping in mappings:
            source_path = mapping.get('source_path', '')
            target_var = mapping.get('target_variable', '')
            
            if not target_var:
                continue
            
            # Extract value from selected item
            value = self.get_nested_value(selected_item, source_path)
            
            # Set in context (null if not found)
            context[target_var] = value
            
            self.logger.debug(
                f"Output mapping: {source_path} -> {target_var}",
                source=source_path,
                target=target_var,
                value_type=type(value).__name__
            )