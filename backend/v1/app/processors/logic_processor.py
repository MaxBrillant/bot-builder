"""
LOGIC_EXPRESSION Processor
Internal conditional routing without user interaction
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, LogicExpressionNodeConfig
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
        node: FlowNode,
        context: Dict[str, Any],
        user_input: Optional[str] = None,
        session: Optional[Any] = None,
        db: Optional[Any] = None
    ) -> ProcessResult:
        """
        Process LOGIC_EXPRESSION node
        
        Args:
            node: Typed FlowNode with LOGIC_EXPRESSION configuration
            context: Session context
            user_input: Not used (logic nodes don't require input)
        
        Returns:
            ProcessResult with next node (no message, immediate routing)
        
        Raises:
            NoMatchingRouteError: If no route condition matches
        """
        # Type narrow config for IDE support (config is empty for logic nodes)
        config: LogicExpressionNodeConfig = node.config

        # Check if node has routes
        has_routes = node.routes and len(node.routes) > 0

        if not has_routes:
            # No routes = terminal node
            self.logger.debug(
                f"LOGIC node '{node.id}' has no routes - terminal node",
                node_id=node.id
            )
            return ProcessResult(
                next_node=None,
                context=context
            )

        # Evaluate routes immediately (no message, no input)
        next_node = self.evaluate_routes(node.routes, context, node.type)

        if next_node is None:
            # Routes exist but none matched - this is an error
            self.logger.error(
                f"No matching route in LOGIC node '{node.id}'",
                node_id=node.id,
                routes_count=len(node.routes)
            )
            raise NoMatchingRouteError(
                f"No route condition matched in LOGIC node '{node.id}'",
                node_id=node.id
            )

        self.logger.debug(
            f"LOGIC routing to {next_node}",
            next_node=next_node
        )

        return ProcessResult(
            next_node=next_node,
            context=context
        )