"""
Conversation Engine - Refactored
Orchestrates flow execution with clean separation of concerns

Three focused classes:
- KeywordMatcher: Matches trigger keywords to flows
- FlowExecutor: Executes flow nodes with auto-progression
- ConversationOrchestrator: Main entry point for message processing
"""

from typing import Optional, Dict, Any, Callable, Awaitable
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import httpx

from app.config import settings
from app.repositories.flow_repository import FlowRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.core.template_engine import TemplateEngine
from app.core.conditions import ConditionEvaluator, sort_routes
from app.core.input_validator import InputValidator as ValidationSystem
from app.core.session_manager import SessionManager
from app.models.flow import Flow
from app.models.session import Session
from app.models.node_configs import FlowNode
from app.models.audit_log import AuditResult
from app.processors.base_processor import ProcessResult
from app.processors.factory import ProcessorFactory
from app.utils.logger import get_logger
from app.utils.constants import NodeType, ErrorMessages, SystemConstraints
from app.utils.exceptions import (
    SessionExpiredError,
    SessionLockError,
    NoMatchingRouteError,
    MaxAutoProgressionError
)

logger = get_logger(__name__)

# ===== Message Callback Constants =====
IS_INTERMEDIATE = False
IS_FINAL = True

# ===== Message Callback Type =====
# Callback signature: async fn(message: str, is_final: bool) -> None
# Used for real-time message delivery (SSE streaming, WhatsApp, etc.)
MessageCallback = Callable[[str, bool], Awaitable[None]]

# ===== Shared HTTP Client Management =====
_http_client: Optional[httpx.AsyncClient] = None
_http_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """
    Get shared HTTP client instance with lazy initialization
    Uses double-checked locking to prevent race conditions

    Returns:
        Shared httpx.AsyncClient
    """
    global _http_client

    # Fast path - client already initialized
    if _http_client is not None:
        return _http_client

    # Slow path - need to initialize with lock
    async with _http_client_lock:
        # Check again after acquiring lock (another task might have initialized)
        if _http_client is None:
            _http_client = httpx.AsyncClient(
                timeout=settings.http_client.timeout,
                follow_redirects=False,
                verify=True,  # Explicitly enable SSL/TLS certificate verification (security requirement)
                limits=httpx.Limits(
                    max_connections=settings.http_client.max_connections,
                    max_keepalive_connections=settings.http_client.max_keepalive
                )
            )
            logger.info("HTTP client lazy initialized with SSL verification enabled")

        return _http_client


async def init_http_client():
    """
    Initialize shared HTTP client (called on app startup)
    Safe to call multiple times - uses same initialization as get_http_client()
    """
    await get_http_client()


async def close_http_client():
    """Close shared HTTP client (called on app shutdown)"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")


# ===== Class 1: KeywordMatcher (~90 lines) =====
class KeywordMatcher:
    """
    Matches trigger keywords to flows within a bot

    Responsibilities:
    - Bot-scoped keyword matching
    - Case-insensitive matching
    - Wildcard fallback support
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize keyword matcher

        Args:
            db: Database session
        """
        self.db = db
        self.flow_repo = FlowRepository(db)
        self.logger = get_logger(__name__)

    async def find_flow_by_keyword(
        self,
        keyword: str,
        bot_id: UUID
    ) -> Optional[Flow]:
        """
        Find flow matching trigger keyword within specific bot

        Args:
            keyword: User's message (potential trigger keyword)
            bot_id: Bot ID to search within

        Returns:
            Flow if keyword matches, None otherwise

        Note:
            - Bot-scoped search (only searches within specified bot)
            - Case-insensitive matching
            - Whitespace trimmed
            - Punctuation NOT allowed (spec line 279: "START!" should NOT match "START")
            - Standalone messages only
            - Wildcard "*" acts as fallback if no specific keyword matches
        """
        # Normalize keyword - convert to uppercase to match stored format
        normalized = keyword.strip().upper()

        # Step 1: Try specific keyword match using repository
        flow = await self.flow_repo.get_by_trigger_keyword(bot_id, normalized)

        if flow:
            self.logger.info(
                f"Flow matched by specific keyword",
                keyword=normalized,
                bot_id=str(bot_id),
                flow_id=str(flow.id),
                flow_name=flow.name
            )
            return flow

        # Step 2: Fallback to wildcard "*"
        wildcard_flow = await self.flow_repo.get_by_wildcard_trigger(bot_id)

        if wildcard_flow:
            self.logger.info(
                f"Flow matched by wildcard for message",
                keyword=normalized,
                bot_id=str(bot_id),
                flow_id=str(wildcard_flow.id),
                flow_name=wildcard_flow.name
            )

        return wildcard_flow


# ===== Class 2: FlowExecutor (~240 lines) =====
class FlowExecutor:
    """
    Executes flow nodes with auto-progression

    Responsibilities:
    - Execute nodes using appropriate processors
    - Manage auto-progression loop
    - Evaluate routes
    - Handle processor errors
    - Track progression count
    """

    def __init__(
        self,
        db: AsyncSession,
        template_engine: TemplateEngine,
        condition_evaluator: ConditionEvaluator,
        validation_system: ValidationSystem,
        session_manager: SessionManager,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        """
        Initialize flow executor

        Args:
            db: Database session
            template_engine: Template rendering engine
            condition_evaluator: Route condition evaluator
            validation_system: Input validation system
            session_manager: Session lifecycle manager
            http_client: Optional HTTP client for API actions
        """
        self.db = db
        self.template_engine = template_engine
        self.condition_evaluator = condition_evaluator
        self.validation_system = validation_system
        self.session_manager = session_manager
        self.logger = get_logger(__name__)
        self.audit_log = AuditLogRepository(db)

        # Initialize processor factory with dependency injection
        self.processor_factory = ProcessorFactory(
            template_engine=template_engine,
            condition_evaluator=condition_evaluator,
            validation_system=validation_system,
            http_client=http_client,
            session_manager=session_manager
        )

    def _build_error_response(self, session: Session, error_message: str) -> Dict[str, Any]:
        """
        Build standardized error response dictionary

        Args:
            session: Active session
            error_message: Error message to return

        Returns:
            Response dictionary with error message and terminated session
        """
        return {
            "messages": [error_message],
            "session_active": False,
            "session_ended": True
        }

    def _build_response(
        self,
        session: Session,
        messages: list,
        active: bool,
        ended: bool
    ) -> Dict[str, Any]:
        """
        Build standardized response dictionary

        Args:
            session: Active session
            messages: List of messages to return
            active: Whether session is still active
            ended: Whether session has ended

        Returns:
            Response dictionary with messages, session status, and session_id
        """
        return {
            "messages": messages,
            "session_active": active,
            "session_ended": ended,
            "session_id": str(session.session_id)
        }

    def _update_message_history(
        self,
        session: Session,
        message: str,
        sender: str,
        node_id: str,
        extra: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Append a message to session history and truncate to 50 entries

        Args:
            session: Active session
            message: Message text
            sender: Who sent it ("user", "bot", "system")
            node_id: Current node ID
            extra: Optional additional fields to include in history entry
        """
        if not session.message_history:
            session.message_history = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender": sender,
            "message": message,
            "node_id": node_id,
        }
        if extra:
            entry.update(extra)

        session.message_history.append(entry)

        # Limit history size to last 50 messages
        if len(session.message_history) > 50:
            session.message_history = session.message_history[-50:]

    def _inject_user_context(
        self,
        node_type: str,
        context: Dict[str, Any],
        user_context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Return enhanced context for API_ACTION nodes, plain context otherwise

        Per BOT_BUILDER_SPECIFICATIONS.md Section 5, Template Contexts by Node:
        - API_ACTION nodes can access {{user.channel_id}} and {{user.channel}}
        - Other node types must NOT have access

        Args:
            node_type: The node type being processed
            context: Current session context
            user_context: User context dict (channel, channel_id)

        Returns:
            Context dict, enhanced with user key for API_ACTION nodes only
        """
        if node_type == NodeType.API_ACTION:
            return {**context, "user": user_context}
        return context

    async def _handle_terminal(
        self,
        session: Session,
        result: ProcessResult,
        messages: list,
        message_callback: MessageCallback
    ) -> Dict[str, Any]:
        """
        Handle session completion for terminal nodes

        Args:
            session: Active session
            result: Process result from the terminal node
            messages: Accumulated messages list
            message_callback: Callback for real-time message delivery

        Returns:
            Response dictionary with ended session
        """
        if result.status == "ERROR":
            await self.session_manager.error_session(session.session_id)
            self.logger.log_session_event(
                str(session.session_id),
                "error",
                flow_id=str(session.flow_id),
                terminal_node=session.current_node_id,
                reason="validation_failure"
            )
        else:
            await self.session_manager.complete_session(session.session_id)
            self.logger.log_session_event(
                str(session.session_id),
                "completed",
                flow_id=str(session.flow_id),
                terminal_node=session.current_node_id
            )

        # Signal completion via callback
        await message_callback("", IS_FINAL)

        return self._build_response(session, messages, active=False, ended=True)

    async def _process_single_node(
        self,
        session: Session,
        node: FlowNode,
        processor,
        user_input: Optional[str],
        user_context: Dict[str, str]
    ) -> ProcessResult:
        """
        Inject user context, invoke processor, and clean up user context from result

        Args:
            session: Active session
            node: Parsed FlowNode to process
            processor: Processor instance (already created by factory)
            user_input: User's input (or None)
            user_context: User context for templates

        Returns:
            ProcessResult from the processor
        """
        node_type = node.type

        enhanced_context = self._inject_user_context(
            node_type, session.context, user_context
        )

        result: ProcessResult = await processor.process(
            node,
            enhanced_context,
            user_input,
            session,
            self.db
        )

        # Remove user context before saving (don't persist in session)
        if "user" in result.context:
            result.context.pop("user")

        return result

    async def execute_flow(
        self,
        session: Session,
        user_input: Optional[str],
        user_context: Dict[str, str],
        message_callback: MessageCallback
    ) -> Dict[str, Any]:
        """
        Execute flow from current node

        Args:
            session: Active session
            user_input: User's input (None if starting flow)
            user_context: User context for templates (channel, channel_id)
            message_callback: Async callback for real-time message delivery.
                              Called with (message, is_final) for each message generated.
                              Required - all callers must provide a callback.

        Returns:
            Response dictionary with messages and session info

        Note:
            All operations are atomic - commit on success or rollback on exception
        """
        messages = []
        auto_progression_count = 0

        # Track user input in message history (if provided)
        if user_input is not None:
            self._update_message_history(
                session, user_input, "user", session.current_node_id
            )

        while True:
            # Check max auto-progression
            if auto_progression_count >= SystemConstraints.MAX_AUTO_PROGRESSION:
                await self.session_manager.error_session(session.session_id)
                raise MaxAutoProgressionError(
                    message="Maximum auto-progression limit reached",
                    error_code="MAX_AUTO_PROGRESSION",
                    limit=SystemConstraints.MAX_AUTO_PROGRESSION
                )

            # Get current node from flow snapshot
            flow_def = session.flow_snapshot
            nodes = flow_def.get('nodes', {})
            current_node_dict = nodes.get(session.current_node_id)

            if not current_node_dict:
                self.logger.error(
                    f"Node not found in flow",
                    node_id=session.current_node_id,
                    session_id=str(session.session_id)
                )
                await self.session_manager.error_session(session.session_id)
                raise NoMatchingRouteError(
                    message=f"Node '{session.current_node_id}' not found",
                    error_code="NODE_NOT_FOUND",
                    node_id=session.current_node_id
                )

            # Sort routes by priority before parsing node
            if 'routes' in current_node_dict and current_node_dict['routes']:
                node_type_for_sorting = current_node_dict.get('type')
                sorted_routes = sort_routes(current_node_dict['routes'], node_type_for_sorting)
                current_node_dict['routes'] = sorted_routes

                self.logger.debug(
                    f"Routes sorted for node '{session.current_node_id}'",
                    node_type=node_type_for_sorting,
                    route_count=len(sorted_routes),
                    conditions=[r.get('condition') for r in sorted_routes]
                )

            # Parse node from dict to FlowNode model (with sorted routes)
            current_node = FlowNode.model_validate(current_node_dict)
            node_type = current_node.type

            # Get processor for node type (narrow ValueError catch)
            try:
                processor = self.processor_factory.create(node_type)
            except ValueError as e:
                self.logger.error(f"Unknown node type: {node_type}", error=str(e))
                await self.session_manager.error_session(session.session_id)
                await message_callback(ErrorMessages.GENERIC_ERROR, IS_FINAL)
                return self._build_error_response(session, ErrorMessages.GENERIC_ERROR)

            # Log and audit node execution
            self.logger.log_flow_execution(
                str(session.flow_id),
                session.current_node_id,
                node_type=node_type,
                has_input=user_input is not None
            )
            await self.audit_log.log_flow_execution(
                action="node_executed",
                flow_id=str(session.flow_id),
                node_id=session.current_node_id,
                bot_id=str(session.bot_id),
                result=AuditResult.SUCCESS,
                event_metadata={
                    "node_type": node_type.value if hasattr(node_type, 'value') else str(node_type),
                    "session_id": str(session.session_id),
                    "has_user_input": user_input is not None
                }
            )

            # Process the node
            try:
                result = await self._process_single_node(
                    session, current_node, processor, user_input, user_context
                )
            except Exception as e:
                self.logger.error(
                    f"Processor error: {str(e)}",
                    node_id=session.current_node_id,
                    node_type=node_type
                )
                await self.session_manager.error_session(session.session_id)
                await message_callback(ErrorMessages.GENERIC_ERROR, IS_FINAL)
                return self._build_error_response(session, ErrorMessages.GENERIC_ERROR)

            # Handle result message
            if result.message:
                messages.append(result.message)
                await message_callback(result.message, IS_INTERMEDIATE)
                self._update_message_history(
                    session, result.message, "bot", session.current_node_id,
                    extra={"node_type": node_type.value if hasattr(node_type, 'value') else str(node_type)}
                )

            # Update session context
            session.context = result.context

            # Check if node needs user input
            if result.needs_input:
                session.auto_progression_count = 0
                await self.db.commit()
                await message_callback("", IS_FINAL)
                return self._build_response(session, messages, active=True, ended=False)

            # Check if current node has routes (for terminal detection)
            node_has_routes = current_node.routes and len(current_node.routes) > 0

            # Terminal: processor set terminal flag, or node has no routes and no next_node
            if result.terminal or (not node_has_routes and result.next_node is None):
                return await self._handle_terminal(
                    session, result, messages, message_callback
                )

            # Error: node HAS routes but no match found (no next_node)
            if result.next_node is None and node_has_routes:
                await self.session_manager.error_session(session.session_id)
                self.logger.warning(
                    f"No next node - routes exist but none matched",
                    node_id=session.current_node_id,
                    session_id=str(session.session_id)
                )
                messages.append(ErrorMessages.NO_ROUTE_MATCH)
                await message_callback(ErrorMessages.NO_ROUTE_MATCH, IS_FINAL)
                self._update_message_history(
                    session, ErrorMessages.NO_ROUTE_MATCH, "system",
                    session.current_node_id,
                    extra={"error_type": "no_route_match"}
                )
                return self._build_response(session, messages, active=False, ended=True)

            # Move to next node
            session.current_node_id = result.next_node
            session.context = result.context

            # Increment auto-progression counter
            auto_progression_count += 1
            session.auto_progression_count += 1

            if session.auto_progression_count > SystemConstraints.MAX_AUTO_PROGRESSION:
                await self.session_manager.error_session(session.session_id)
                raise MaxAutoProgressionError(
                    message="Maximum auto-progression limit reached",
                    error_code="MAX_AUTO_PROGRESSION",
                    limit=SystemConstraints.MAX_AUTO_PROGRESSION
                )

            # Clear user input for next iteration (auto-progression)
            user_input = None


# ===== Class 3: ConversationOrchestrator (~100 lines) =====
class ConversationOrchestrator:
    """
    Main conversation orchestration entry point

    Responsibilities:
    - Process incoming messages
    - Get or create sessions
    - Match trigger keywords
    - Coordinate keyword matcher and flow executor
    - Handle global errors
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize conversation orchestrator

        Args:
            db: Database session
        """
        self.db = db
        self.logger = get_logger(__name__)
        self._http_client: Optional[httpx.AsyncClient] = None

        # Initialize core components
        template_engine = TemplateEngine()
        condition_evaluator = ConditionEvaluator()
        validation_system = ValidationSystem()
        session_manager = SessionManager(db)

        # Initialize focused components
        self.keyword_matcher = KeywordMatcher(db)
        self.flow_executor = FlowExecutor(
            db,
            template_engine,
            condition_evaluator,
            validation_system,
            session_manager,
            http_client=None  # Will be initialized lazily on first use
        )
        self.session_manager = session_manager

    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized (lazy initialization)"""
        if self._http_client is None:
            self._http_client = await get_http_client()
            # Update factory's http_client
            self.flow_executor.processor_factory.http_client = self._http_client

    async def process_message(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: UUID,
        message: str,
        message_callback: MessageCallback
    ) -> Dict[str, Any]:
        """
        Main entry point for message processing

        Args:
            channel: Communication channel (whatsapp, sms, telegram, etc.)
            channel_user_id: User identifier in the channel
            bot_id: Bot ID processing this message
            message: User's message text
            message_callback: Async callback for real-time message delivery.
                              Called with (message, is_final) for each message generated.
                              Required - all callers must provide a callback.

        Returns:
            Response dictionary with messages and session info
        """
        # Ensure HTTP client is initialized (lazy initialization)
        await self._ensure_http_client()

        try:
            # Try to get existing session with lock to prevent concurrent updates
            # The lock is held for the duration of flow execution
            session = await self.session_manager.get_active_session(
                channel,
                channel_user_id,
                bot_id,
                for_update=True  # Lock session to prevent concurrent modification
            )

            if session is None:
                # No active session - check for trigger keyword (bot-scoped)
                flow = await self.keyword_matcher.find_flow_by_keyword(message, bot_id)
                if flow is None:
                    await message_callback("Unknown command. Please try again.", True)
                    return {
                        "messages": ["Unknown command. Please try again."],
                        "session_active": False,
                        "session_ended": False
                    }

                # Create new session with flow snapshot
                session = await self.session_manager.create_session(
                    channel,
                    channel_user_id,
                    bot_id,
                    flow.id,
                    flow.flow_definition
                )

                self.logger.log_user_action(
                    channel_user_id,
                    "flow_started",
                    channel=channel,
                    bot_id=str(bot_id),
                    flow_id=str(flow.id)
                )

                # Start flow execution (no user input on first call)
                user_context = {
                    "channel": channel,
                    "channel_id": channel_user_id
                }
                return await self.flow_executor.execute_flow(
                    session, None, user_context, message_callback=message_callback
                )

            # Check timeout
            if self.session_manager.check_timeout(session):
                await self.session_manager.expire_session(session.session_id)

                self.logger.log_user_action(
                    channel_user_id,
                    "session_expired",
                    channel=channel,
                    session_id=str(session.session_id)
                )

                await message_callback(ErrorMessages.SESSION_EXPIRED, True)
                return {
                    "messages": [ErrorMessages.SESSION_EXPIRED],
                    "session_active": False,
                    "session_ended": True
                }

            # Continue existing session
            user_context = {
                "channel": channel,
                "channel_id": channel_user_id
            }
            return await self.flow_executor.execute_flow(
                session, message, user_context, message_callback=message_callback
            )

        except SessionLockError:
            # Another request is already processing this session
            # Return a friendly message to the user
            msg = "Your previous message is still being processed. Please wait a moment."
            await message_callback(msg, True)
            return {
                "messages": [msg],
                "session_active": True,
                "session_ended": False
            }

        except SessionExpiredError:
            await message_callback(ErrorMessages.SESSION_EXPIRED, True)
            return {
                "messages": [ErrorMessages.SESSION_EXPIRED],
                "session_active": False,
                "session_ended": True
            }

        except MaxAutoProgressionError:
            await message_callback(ErrorMessages.MAX_AUTO_PROGRESSION, True)
            return {
                "messages": [ErrorMessages.MAX_AUTO_PROGRESSION],
                "session_active": False,
                "session_ended": True
            }

        except NoMatchingRouteError as e:
            self.logger.error(f"No matching route: {str(e)}")
            await message_callback(ErrorMessages.NO_ROUTE_MATCH, True)
            return {
                "messages": [ErrorMessages.NO_ROUTE_MATCH],
                "session_active": False,
                "session_ended": True
            }

        except Exception as e:
            self.logger.error(f"Conversation error: {str(e)}", error=str(e))
            await message_callback(ErrorMessages.GENERIC_ERROR, True)
            return {
                "messages": [ErrorMessages.GENERIC_ERROR],
                "session_active": False,
                "session_ended": True
            }


# ===== Backward Compatibility Alias =====
# For existing code that imports ConversationEngine
ConversationEngine = ConversationOrchestrator
