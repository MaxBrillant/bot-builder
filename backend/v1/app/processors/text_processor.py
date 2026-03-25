"""
TEXT Processor
Display text information and auto-progress to next node
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, TextNodeConfig
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor(BaseProcessor):
    """
    Process TEXT nodes - display text information

    Features:
    - Display templated text message to user
    - Auto-progress to next node (no user input required)
    - Access full context for templates

    Use Cases:
    - Success confirmations
    - Error messages
    - Informational notifications
    - Intermediate status updates
    - Terminal farewell messages (no routes)

    Note:
    - Cannot wait for user input
    - Cannot validate anything
    - Cannot save to context
    - Nodes without routes are terminal
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
        Process TEXT node

        Args:
            node: Typed FlowNode with TEXT configuration
            context: Session context
            user_input: Not used (text nodes don't require input)
        
        Returns:
            ProcessResult with message and next node
        
        Raises:
            NoMatchingRouteError: If no route matches
        """
        # Type narrow config for IDE support
        config: TextNodeConfig = node.config

        # Render message with context variables (with error handling)
        try:
            message = self.template_engine.render(config.text, context)
        except Exception as e:
            self.logger.error(
                f"Template rendering error in TEXT node '{node.id}': {str(e)}",
                node_id=node.id,
                error=str(e)
            )
            # Fallback to unrendered text to avoid flow crash
            message = f"Error rendering message: {config.text[:100]}..."

        self.logger.debug(
            f"TEXT node displaying",
            node_id=node.id,
            message_length=len(message)
        )

        # Check if node is terminal (has no routes)
        terminal = self.check_terminal(node, context, message=message)
        if terminal:
            return terminal

        # Evaluate routes for next node
        next_node = self.evaluate_routes(node.routes, context, node.type)

        if next_node is None:
            self.raise_no_matching_route(node)

        return ProcessResult(
            message=message,
            next_node=next_node,
            context=context
        )