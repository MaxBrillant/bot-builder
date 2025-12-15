"""
MESSAGE Processor
Display information and auto-progress to next node
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, MessageNodeConfig
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger
from app.utils.exceptions import NoMatchingRouteError

logger = get_logger(__name__)


class MessageProcessor(BaseProcessor):
    """
    Process MESSAGE nodes - display information
    
    Features:
    - Display templated message to user
    - Auto-progress to next node (no user input required)
    - Access full context for templates
    
    Use Cases:
    - Success confirmations
    - Error messages
    - Informational notifications
    - Intermediate status updates
    
    Note:
    - Cannot wait for user input
    - Cannot validate anything
    - Cannot save to context
    - Must have a next node in routes
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
        Process MESSAGE node
        
        Args:
            node: Typed FlowNode with MESSAGE configuration
            context: Session context
            user_input: Not used (message nodes don't require input)
        
        Returns:
            ProcessResult with message and next node
        
        Raises:
            NoMatchingRouteError: If no route matches
        """
        # Type narrow config for IDE support
        config: MessageNodeConfig = node.config
        
        # Render message with context variables
        message = self.template_engine.render(config.text, context)
        
        self.logger.debug(
            f"MESSAGE node displaying",
            node_id=node.id,
            message_length=len(message)
        )
        
        # Evaluate routes for next node
        next_node = self.evaluate_routes(node.routes, context, node.type)
        
        if next_node is None:
            self.logger.error(
                f"No matching route in MESSAGE node '{node.id}'",
                node_id=node.id
            )
            raise NoMatchingRouteError(
                f"No route condition matched in MESSAGE node '{node.id}'",
                node_id=node.id
            )
        
        return ProcessResult(
            message=message,
            next_node=next_node,
            context=context
        )