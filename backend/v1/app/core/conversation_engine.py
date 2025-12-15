"""
Conversation Engine
Orchestrates flow execution and manages conversation lifecycle
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import httpx

from app.config import settings
from app.core.template_engine import TemplateEngine
from app.core.condition_evaluator import ConditionEvaluator
from app.core.validation_system import ValidationSystem
from app.core.session_manager import SessionManager
from app.core.route_sorter import sort_routes
from app.models.flow import Flow
from app.models.session import Session
from app.models.node_configs import FlowNode
from app.processors.base_processor import ProcessResult
from app.processors.prompt_processor import PromptProcessor
from app.processors.menu_processor import MenuProcessor
from app.processors.api_action_processor import APIActionProcessor
from app.processors.logic_processor import LogicProcessor
from app.processors.message_processor import MessageProcessor
from app.processors.end_processor import EndProcessor
from app.utils.logger import get_logger
from app.utils.constants import NodeType, ErrorMessages, SystemConstraints
from app.utils.exceptions import (
    SessionExpiredError,
    NoMatchingRouteError,
    MaxAutoProgressionError,
    FlowNotFoundError
)

logger = get_logger(__name__)

# Shared HTTP client for all conversation engines (managed at app lifecycle)
_http_client: Optional[httpx.AsyncClient] = None
_http_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """
    Get shared HTTP client instance with lazy initialization.
    Uses double-checked locking to prevent race conditions.
    
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
                timeout=settings.HTTP_TIMEOUT,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=settings.HTTP_MAX_CONNECTIONS,
                    max_keepalive_connections=settings.HTTP_MAX_KEEPALIVE
                )
            )
            logger.info("HTTP client lazy initialized")
        
        return _http_client


async def init_http_client():
    """
    Initialize shared HTTP client (called on app startup).
    Safe to call multiple times - uses same initialization as get_http_client().
    """
    await get_http_client()


async def close_http_client():
    """Close shared HTTP client (called on app shutdown)"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")


class ConversationEngine:
    """
    Main conversation orchestration engine
    
    Responsibilities:
    - Process incoming messages
    - Match trigger keywords (bot-scoped)
    - Load and execute flows
    - Manage node progression
    - Track auto-progression limit
    - Handle timeouts
    - Coordinate with processors
    - Error handling and recovery
    - Provide bot and user context to processors
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize conversation engine
        
        Args:
            db: Database session
        """
        self.db = db
        self.logger = get_logger(__name__)
        
        # Initialize core components
        self.template_engine = TemplateEngine()
        self.condition_evaluator = ConditionEvaluator()
        self.validation_system = ValidationSystem()
        self.session_manager = SessionManager(db)
        
        # Processors will get HTTP client lazily when needed
        # Don't block __init__ waiting for HTTP client initialization
        self.processors = {
            NodeType.PROMPT.value: PromptProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system
            ),
            NodeType.MENU.value: MenuProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system
            ),
            NodeType.API_ACTION.value: APIActionProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system,
                http_client=None  # Will be set lazily on first use
            ),
            NodeType.LOGIC_EXPRESSION.value: LogicProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system
            ),
            NodeType.MESSAGE.value: MessageProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system
            ),
            NodeType.END.value: EndProcessor(
                self.template_engine,
                self.condition_evaluator,
                self.validation_system
            )
        }
    
    async def process_message(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: UUID,
        message: str
    ) -> Dict[str, Any]:
        """
        Main entry point for message processing
        
        Args:
            channel: Communication channel (whatsapp, sms, telegram, etc.)
            channel_user_id: User identifier in the channel
            bot_id: Bot ID processing this message
            message: User's message text
        
        Returns:
            Response dictionary with messages and session info
        """
        try:
            # Get or create session
            session = await self.session_manager.get_active_session(
                channel,
                channel_user_id,
                bot_id
            )
            
            if session is None:
                # No active session - check for trigger keyword (bot-scoped)
                flow = await self._find_flow_by_keyword(message, bot_id)
                if flow is None:
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
                # Add user context for templates
                user_context = {
                    "channel": channel,
                    "channel_id": channel_user_id
                }
                return await self._execute_flow(session, None, user_context)
            
            # Check timeout
            if self.session_manager.check_timeout(session):
                await self.session_manager.expire_session(session.session_id)
                
                self.logger.log_user_action(
                    channel_user_id,
                    "session_expired",
                    channel=channel,
                    session_id=str(session.session_id)
                )
                
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
            return await self._execute_flow(session, message, user_context)
            
        except SessionExpiredError:
            return {
                "messages": [ErrorMessages.SESSION_EXPIRED],
                "session_active": False,
                "session_ended": True
            }
        
        except MaxAutoProgressionError:
            return {
                "messages": [ErrorMessages.MAX_AUTO_PROGRESSION],
                "session_active": False,
                "session_ended": True
            }
        
        except NoMatchingRouteError as e:
            self.logger.error(f"No matching route: {str(e)}")
            return {
                "messages": [ErrorMessages.NO_ROUTE_MATCH],
                "session_active": False,
                "session_ended": True
            }
        
        except Exception as e:
            self.logger.error(f"Conversation error: {str(e)}", error=str(e))
            return {
                "messages": [ErrorMessages.GENERIC_ERROR],
                "session_active": False,
                "session_ended": True
            }
    
    async def _find_flow_by_keyword(self, keyword: str, bot_id: UUID) -> Optional[Flow]:
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
            - Trailing punctuation ignored
            - Standalone messages only
            - Wildcard "*" acts as fallback if no specific keyword matches
        """
        # Normalize keyword - convert to uppercase to match stored format
        normalized = keyword.strip().upper()
        # Remove trailing punctuation
        normalized = normalized.rstrip('!.?')
        
        # Step 1: Try specific keyword match
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            Flow.trigger_keywords.contains([normalized])
        )
        
        result = await self.db.execute(stmt)
        flow = result.scalar_one_or_none()
        
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
        stmt = select(Flow).where(
            Flow.bot_id == bot_id,
            Flow.trigger_keywords.contains(["*"])
        )
        
        result = await self.db.execute(stmt)
        wildcard_flow = result.scalar_one_or_none()
        
        if wildcard_flow:
            self.logger.info(
                f"Flow matched by wildcard for message",
                keyword=normalized,
                bot_id=str(bot_id),
                flow_id=str(wildcard_flow.id),
                flow_name=wildcard_flow.name
            )
        
        return wildcard_flow
    
    async def _execute_flow(
        self,
        session: Session,
        user_input: Optional[str],
        user_context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Execute flow from current node
        
        Args:
            session: Active session
            user_input: User's input (None if starting flow)
            user_context: User context for templates (channel, channel_id)
        
        Returns:
            Response dictionary with messages and session info
            
        Note:
            Database transaction is managed by FastAPI's get_db dependency.
            All operations in this method are atomic - they commit on success
            or rollback on exception automatically.
        """
        messages = []
        auto_progression_count = 0
        
        while True:
            # Check max auto-progression
            if auto_progression_count >= SystemConstraints.MAX_AUTO_PROGRESSION:
                await self.session_manager.error_session(session.session_id)
                raise MaxAutoProgressionError()
            
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
                    f"Node '{session.current_node_id}' not found",
                    node_id=session.current_node_id
                )
            
            # Sort routes by priority before parsing node (spec requirement)
            # Routes are sorted at runtime to ensure optimal evaluation order
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

            # Get processor for node type
            node_type = current_node.type
            processor = self.processors.get(node_type)
            
            if not processor:
                self.logger.error(f"Unknown node type: {node_type}")
                await self.session_manager.error_session(session.session_id)
                return {
                    "messages": [ErrorMessages.GENERIC_ERROR],
                    "session_active": False,
                    "session_ended": True
                }
            
            # Process node
            self.logger.log_flow_execution(
                str(session.flow_id),
                session.current_node_id,
                node_type=node_type,
                has_input=user_input is not None
            )
            
            try:
                # Ensure HTTP client is initialized for API_ACTION nodes
                if node_type == NodeType.API_ACTION.value:
                    api_processor = self.processors[NodeType.API_ACTION.value]
                    if api_processor.http_client is None:
                        api_processor.http_client = await get_http_client()
                
                # Inject user context for template rendering
                # Processors can access {{user.channel_id}} and {{user.channel}}
                enhanced_context = {
                    **session.context,
                    "user": user_context
                }
                
                result: ProcessResult = await processor.process(
                    current_node,
                    enhanced_context,
                    user_input,
                    session,
                    self.db
                )
                
                # Remove user context before saving (don't persist in session)
                if "user" in result.context:
                    result.context.pop("user")
            except Exception as e:
                self.logger.error(
                    f"Processor error: {str(e)}",
                    node_id=session.current_node_id,
                    node_type=node_type
                )
                await self.session_manager.error_session(session.session_id)
                return {
                    "messages": [ErrorMessages.GENERIC_ERROR],
                    "session_active": False,
                    "session_ended": True
                }
            
            # Handle result message
            if result.message:
                messages.append(result.message)
            
            # Update session context
            session.context = result.context
            
            # Check if node needs user input
            if result.needs_input:
                # Update in-memory session object (FastAPI's get_db will commit)
                session.context = result.context
                session.auto_progression_count = 0
                
                return {
                    "messages": messages,
                    "session_active": True,
                    "session_ended": False,
                    "session_id": str(session.session_id)
                }
            
            # Check if terminal node (END)
            if result.terminal:
                await self.session_manager.complete_session(session.session_id)
                
                self.logger.log_session_event(
                    str(session.session_id),
                    "completed",
                    flow_id=str(session.flow_id)
                )
                
                return {
                    "messages": messages,
                    "session_active": False,
                    "session_ended": True,
                    "session_id": str(session.session_id)
                }
            
            # Check if no next node (error)
            if result.next_node is None:
                await self.session_manager.error_session(session.session_id)
                
                self.logger.warning(
                    f"No next node",
                    node_id=session.current_node_id,
                    session_id=str(session.session_id)
                )
                
                messages.append(ErrorMessages.NO_ROUTE_MATCH)
                return {
                    "messages": messages,
                    "session_active": False,
                    "session_ended": True,
                    "session_id": str(session.session_id)
                }
            
            # Move to next node (update in-memory object)
            session.current_node_id = result.next_node
            session.context = result.context
            
            # Increment auto-progression counter (in-memory)
            auto_progression_count += 1
            session.auto_progression_count += 1
            
            # Check limit
            if session.auto_progression_count > SystemConstraints.MAX_AUTO_PROGRESSION:
                await self.session_manager.error_session(session.session_id)
                raise MaxAutoProgressionError()
            
            # Clear user input for next iteration (auto-progression)
            user_input = None