"""
Base Processor
Abstract base class for all node processors
Provides shared functionality for route evaluation and interrupt handling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from app.models.node_configs import FlowNode, Route, Interrupt
from app.core.template_engine import TemplateEngine
from app.core.conditions import ConditionEvaluator
from app.core.input_validator import InputValidator as ValidationSystem
from app.utils.logger import get_logger


@dataclass
class ProcessResult:
    """
    Result of node processing
    
    Fields:
        message: Optional message to send to user
        needs_input: Whether processor needs user input (wait state)
        next_node: ID of next node to execute (None if needs input or terminal)
        context: Updated context dictionary
        terminal: Whether this node terminates the conversation
        status: Optional status indicator (e.g., 'COMPLETED', 'ERROR')
    """
    message: Optional[str] = None
    needs_input: bool = False
    next_node: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    terminal: bool = False
    status: Optional[str] = None


class BaseProcessor(ABC):
    """
    Abstract base class for node processors
    
    All node type processors inherit from this class and implement
    the process() method with their specific logic.
    
    Shared functionality:
    - Route evaluation
    - Interrupt checking
    - Template rendering access
    - Validation access
    - Condition evaluation access
    """
    
    def __init__(
        self,
        template_engine: TemplateEngine,
        condition_evaluator: ConditionEvaluator,
        validation_system: ValidationSystem
    ):
        """
        Initialize processor with shared dependencies
        
        Args:
            template_engine: Template rendering engine
            condition_evaluator: Condition evaluation engine
            validation_system: Input validation system
        """
        self.template_engine = template_engine
        self.condition_evaluator = condition_evaluator
        self.validation_system = validation_system
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def process(
        self,
        node: FlowNode,
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process node and return result
        
        Args:
            node: Typed FlowNode instance from flow
            context: Current session context
            user_input: User's input message (None if first call or auto-progression)
            session: Session instance (for retry tracking)
            db: Database session (AsyncSession)
        
        Returns:
            ProcessResult with execution outcome
        
        Note:
            Must be implemented by each processor subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement process() method"
        )
    
    def evaluate_routes(
        self,
        routes: List[Route],
        context: Dict[str, Any],
        node_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Evaluate routes in order, return first match

        Args:
            routes: List of typed Route instances (pre-sorted by engine)
            context: Current context for condition evaluation
            node_type: Type of node (unused, kept for backward compatibility)

        Returns:
            target_node ID of first matching route, or None if no match

        Note:
            Routes are already sorted by priority in the engine before reaching this method.
            Specific conditions are evaluated first, catch-all "true" last.
            First matching condition wins.
            If no route matches, returns None (which typically causes error).
        """
        if not routes:
            return None

        # Convert Route objects to dict format for iteration
        routes_as_dicts = [{'condition': r.condition, 'target_node': r.target_node} for r in routes]

        # Note: Routes are already sorted by the engine (see engine.py lines 266-270)
        # No need to sort again here

        for route_dict in routes_as_dicts:
            condition = route_dict['condition']
            target_node = route_dict['target_node']
            
            try:
                if self.condition_evaluator.evaluate(condition, context):
                    self.logger.debug(
                        f"Route matched: {condition} -> {target_node}",
                        condition=condition,
                        target=target_node
                    )
                    return target_node
            except Exception as e:
                self.logger.error(
                    f"Route evaluation error: {str(e)}",
                    condition=condition,
                    error=str(e)
                )
                continue
        
        self.logger.warning("No route matched", route_count=len(routes))
        return None
    
    def check_interrupt(
        self,
        user_input: str,
        interrupts: List[Interrupt]
    ) -> Optional[str]:
        """
        Check if input matches any interrupt keyword
        
        Args:
            user_input: User's input message
            interrupts: List of typed Interrupt instances
        
        Returns:
            target_node ID if interrupt matched, None otherwise
        
        Note:
            - Interrupts are checked before validation
            - Case-insensitive matching
            - Whitespace trimmed before matching
            - Exact match required (after trim and lowercase)
        """
        if not interrupts or not user_input:
            return None
        
        # Trim and lowercase user input for comparison
        trimmed_input = user_input.strip().lower()
        
        for interrupt in interrupts:
            interrupt_keyword = interrupt.input.strip().lower()
            target_node = interrupt.target_node
            
            if trimmed_input == interrupt_keyword:
                self.logger.info(
                    f"Interrupt matched: '{interrupt_keyword}' -> {target_node}",
                    keyword=interrupt_keyword,
                    target=target_node
                )
                return target_node
        
        return None
    
    def get_nested_value(self, obj: Any, path: str) -> Any:
        """
        Get nested value from object using dot notation
        
        Args:
            obj: Object to traverse (dict, list, or object)
            path: Dot-notation path (e.g., 'user.profile.name')
        
        Returns:
            Value at path, or None if not found
        
        Examples:
            >>> get_nested_value({'user': {'name': 'John'}}, 'user.name')
            'John'
            
            >>> get_nested_value({'items': [{'id': 1}]}, 'items.0.id')
            1
        """
        if not path:
            return obj
        
        try:
            parts = path.split('.')
            current = obj
            
            for part in parts:
                if current is None:
                    return None
                
                # Handle dictionary access
                if isinstance(current, dict):
                    current = current.get(part)
                
                # Handle list/array access (numeric indices)
                elif isinstance(current, (list, tuple)):
                    try:
                        index = int(part)
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            return None
                    except (ValueError, IndexError):
                        return None
                
                # Handle object attribute access
                elif hasattr(current, part):
                    current = getattr(current, part)
                
                else:
                    return None
            
            return current
            
        except Exception as e:
            self.logger.debug(f"Error getting nested value: {str(e)}", path=path)
            return None
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input by trimming whitespace
        
        Args:
            user_input: Raw user input
        
        Returns:
            Sanitized input
        
        Note:
            As per specification, system automatically trims leading/trailing whitespace.
            No HTML/SQL injection prevention - developer must validate appropriately.
        """
        return user_input.strip() if user_input else ""

    def _get_variable_type(self, var_name: str, context: Dict[str, Any]) -> str:
        """
        Get variable type from flow variables definition

        Args:
            var_name: Variable name
            context: Session context (should contain _flow_variables if defined)

        Returns:
            Variable type string (default: 'STRING')
        """
        flow_variables = context.get('_flow_variables', {})
        if var_name in flow_variables:
            var_def = flow_variables[var_name]
            if isinstance(var_def, dict):
                return var_def.get('type', 'STRING')
        return 'STRING'