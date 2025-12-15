"""
END Processor
Terminates conversation flow
"""

from typing import Optional, Dict, Any
from app.models.node_configs import FlowNode, EndNodeConfig
from app.processors.base_processor import BaseProcessor, ProcessResult
from app.utils.logger import get_logger
from app.utils.constants import SessionStatus

logger = get_logger(__name__)


class EndProcessor(BaseProcessor):
    """
    Process END nodes - terminate conversation
    
    Features:
    - Mark session as COMPLETED
    - No message (use MESSAGE before END if needed)
    - Session cleanup
    - Terminal node (no further execution)
    
    Constraints:
    - Cannot show message
    - Cannot route to other nodes
    - Cannot be bypassed once reached
    - Cannot restart flow automatically
    
    Use Cases:
    - Natural conversation completion
    - Error termination
    - User exit request
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
        Process END node
        
        Args:
            node: Typed FlowNode with END configuration
            context: Session context
            user_input: Not used (END nodes don't process input)
        
        Returns:
            ProcessResult with terminal flag set
        """
        # Type narrow config for IDE support (config is empty for end nodes)
        config: EndNodeConfig = node.config
        
        self.logger.info(
            f"END node reached",
            node_id=node.id
        )
        
        # Terminal node - no message, no next node
        return ProcessResult(
            terminal=True,
            status=SessionStatus.COMPLETED.value,
            context=context
        )