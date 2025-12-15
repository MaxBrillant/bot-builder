"""
Processor Factory
Creates node processors with dependency injection

Eliminates hardcoded processor instantiation from ConversationEngine
and provides extensible registration system for new processor types.
"""

from typing import Dict, Type, Optional
from app.processors.base_processor import BaseProcessor
from app.processors.prompt_processor import PromptProcessor
from app.processors.menu_processor import MenuProcessor
from app.processors.api_action_processor import APIActionProcessor
from app.processors.logic_processor import LogicProcessor
from app.processors.message_processor import MessageProcessor
from app.processors.end_processor import EndProcessor
from app.core.template_engine import TemplateEngine
from app.core.conditions import ConditionEvaluator
from app.core.validators import InputValidator as ValidationSystem
from app.utils.constants import NodeType
from app.utils.logger import get_logger
import httpx

logger = get_logger(__name__)


class ProcessorFactory:
    """
    Factory for creating node processors with dependency injection

    Features:
    - Centralized processor instantiation
    - Dependency injection (no hardcoded dependencies)
    - Extensible registration system
    - Lazy instantiation (create processors on demand)

    Usage:
        factory = ProcessorFactory(
            template_engine=template_engine,
            condition_evaluator=evaluator,
            validation_system=validator,
            http_client=client
        )

        prompt_processor = factory.create(NodeType.PROMPT.value)
    """

    def __init__(
        self,
        template_engine: TemplateEngine,
        condition_evaluator: ConditionEvaluator,
        validation_system: ValidationSystem,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        """
        Initialize processor factory with dependencies

        Args:
            template_engine: Template rendering engine
            condition_evaluator: Route condition evaluator
            validation_system: Input validation system
            http_client: Optional HTTP client for API processors
        """
        self.template_engine = template_engine
        self.condition_evaluator = condition_evaluator
        self.validation_system = validation_system
        self.http_client = http_client

        # Registry of processor types
        self._processors: Dict[str, Type[BaseProcessor]] = {}

        # Cache of instantiated processors (singleton pattern per factory)
        self._instances: Dict[str, BaseProcessor] = {}

        # Register built-in processor types
        self._register_builtin_processors()

        logger.debug("ProcessorFactory initialized with all processor types registered")

    def _register_builtin_processors(self):
        """Register all built-in processor types"""
        self.register(NodeType.PROMPT.value, PromptProcessor)
        self.register(NodeType.MENU.value, MenuProcessor)
        self.register(NodeType.API_ACTION.value, APIActionProcessor)
        self.register(NodeType.LOGIC_EXPRESSION.value, LogicProcessor)
        self.register(NodeType.MESSAGE.value, MessageProcessor)
        self.register(NodeType.END.value, EndProcessor)

    def register(self, node_type: str, processor_class: Type[BaseProcessor]):
        """
        Register a processor type

        Args:
            node_type: Node type identifier (e.g., "PROMPT", "MENU")
            processor_class: Processor class to instantiate

        Note:
            This allows registration of custom processor types at runtime.
            Useful for plugins or extensions.
        """
        if node_type in self._processors:
            logger.warning(
                f"Overwriting existing processor registration for type: {node_type}",
                node_type=node_type,
                previous_class=self._processors[node_type].__name__,
                new_class=processor_class.__name__
            )

        self._processors[node_type] = processor_class
        logger.debug(f"Registered processor: {node_type} -> {processor_class.__name__}")

    def create(self, node_type: str) -> BaseProcessor:
        """
        Create processor instance for given node type

        Args:
            node_type: Node type identifier

        Returns:
            Processor instance with dependencies injected

        Raises:
            ValueError: If node type is not registered

        Note:
            Processors are cached - calling create() multiple times
            for the same node_type returns the same instance.
        """
        # Check cache first
        if node_type in self._instances:
            return self._instances[node_type]

        # Get processor class
        processor_class = self._processors.get(node_type)
        if not processor_class:
            raise ValueError(
                f"Unknown node type: '{node_type}'. "
                f"Registered types: {', '.join(self._processors.keys())}"
            )

        # Instantiate with dependencies
        processor = self._instantiate_processor(node_type, processor_class)

        # Cache instance
        self._instances[node_type] = processor

        logger.debug(
            f"Created processor instance: {node_type}",
            node_type=node_type,
            processor_class=processor_class.__name__
        )

        return processor

    def _instantiate_processor(
        self,
        node_type: str,
        processor_class: Type[BaseProcessor]
    ) -> BaseProcessor:
        """
        Instantiate processor with appropriate dependencies

        Args:
            node_type: Node type identifier
            processor_class: Processor class to instantiate

        Returns:
            Processor instance

        Note:
            APIActionProcessor requires http_client, others don't.
            This method handles the difference.
        """
        # API_ACTION requires http_client
        if node_type == NodeType.API_ACTION.value:
            return processor_class(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system,
                http_client=self.http_client
            )

        # All other processors use standard dependencies
        return processor_class(
            self.template_engine,
            self.condition_evaluator,
            self.validation_system
        )

    def get_registered_types(self) -> list[str]:
        """
        Get list of registered processor types

        Returns:
            List of node type identifiers
        """
        return list(self._processors.keys())

    def clear_cache(self):
        """
        Clear cached processor instances

        Note:
            Forces re-instantiation on next create() call.
            Useful for testing or dynamic reconfiguration.
        """
        self._instances.clear()
        logger.debug("Cleared processor instance cache")
