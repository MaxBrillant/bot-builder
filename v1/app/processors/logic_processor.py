"""
LOGIC_EXPRESSION Processor
Internal conditional routing without user interaction
"""

from typing import Optional, Dict, Any
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger
from app.utils.exceptions import NoMatchingRouteError

logger = get_logger(__name__)


class LogicProcessor(BaseProcessor):
    """
    Process LOGIC_EXPRESSION nodes - conditional routing
    
    Features:
    - Evaluate conditions against context
    - Route to appropriate next node
    - No message display
    - No user input required
    - Immediate progression (auto-progresses)
    
    Use Cases:
    - Branching based on API results
    - Checking if arrays are empty
    - Routing based on user type or status
    - Implementing if-else logic
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
        Process LOGIC_EXPRESSION node
        
        Args:
            node: LOGIC_EXPRESSION node definition
            context: Session context
            user_input: Not used (logic nodes don't require input)
        
        Returns:
            ProcessResult with next node (no message, immediate routing)
        
        Raises:
            NoMatchingRouteError: If no route condition matches
        """
        # Evaluate routes immediately (no message, no input)
        routes = node.get('routes', [])
        next_node = self.evaluate_routes(routes, context)
        
        if next_node is None:
            node_id = node.get('id', 'unknown')
            self.logger.error(
                f"No matching route in LOGIC node '{node_id}'",
                node_id=node_id,
                routes_count=len(routes)
            )
            raise NoMatchingRouteError(
                f"No route condition matched in LOGIC node '{node_id}'",
                node_id=node_id
            )
        
        self.logger.debug(
            f"LOGIC routing to {next_node}",
            next_node=next_node
        )
        
        return ProcessResult(
            next_node=next_node,
            context=context
        )