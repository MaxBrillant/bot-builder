"""
Retry Handler
Centralized retry logic for PROMPT and MENU processors

Consolidates duplicate retry handling code, providing consistent behavior
for validation failures across different node types.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.core.session_manager import SessionManager
from app.core.template_engine import TemplateEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetryResult:
    """
    Result of retry handling

    Attributes:
        should_continue: Whether to continue with retry (show error and wait for new input)
        next_node: Next node to route to (set when max attempts reached and fail_route exists)
        terminal: Whether to terminate the session
        error_message: Error message to display to user
    """
    should_continue: bool
    next_node: Optional[str] = None
    terminal: bool = False
    error_message: str = ""


class RetryHandler:
    """
    Centralized retry logic for validation failures

    Features:
    - Track validation attempts
    - Enforce max attempts limit
    - Route to fail_route when limit reached
    - Terminate session if no fail_route defined
    - Render counter text with attempt information
    - Reset attempts on success or interrupt

    Used by:
    - PromptProcessor: User input validation failures
    - MenuProcessor: Invalid selection handling
    """

    def __init__(
        self,
        session_manager: SessionManager,
        template_engine: TemplateEngine
    ):
        """
        Initialize retry handler

        Args:
            session_manager: Session manager for tracking attempts
            template_engine: Template engine for rendering counter text
        """
        self.session_manager = session_manager
        self.template_engine = template_engine

    async def handle_validation_failure(
        self,
        session: Any,
        context: Dict[str, Any],
        error_message: str
    ) -> RetryResult:
        """
        Handle validation failure with retry logic

        Args:
            session: Current session object
            context: Session context (contains _flow_defaults)
            error_message: Base error message to display

        Returns:
            RetryResult indicating what action to take

        Note:
            - Increments validation attempts counter
            - Checks if max attempts exceeded
            - Routes to fail_route or terminates session when limit reached
            - Appends counter text if configured
        """
        # Increment validation attempts
        new_attempt_count = await self.session_manager.increment_validation_attempts(
            session.session_id
        )

        # Get retry logic from flow defaults
        flow_defaults = context.get('_flow_defaults', {})
        retry_logic = flow_defaults.get('retry_logic', {})
        max_attempts = retry_logic.get('max_attempts', 3)
        fail_route = retry_logic.get('fail_route')  # None = terminate session on max attempts
        counter_text = retry_logic.get('counter_text', '(Attempt {{current_attempt}} of {{max_attempts}})')

        # Check if max attempts exceeded
        if new_attempt_count > max_attempts:
            # Max attempts reached - reset counter
            await self.session_manager.reset_validation_attempts(session.session_id)

            if fail_route:
                # Route to fail_route
                logger.warning(
                    f"Max validation attempts reached, routing to fail_route",
                    attempts=new_attempt_count,
                    max_attempts=max_attempts,
                    fail_route=fail_route
                )
                return RetryResult(
                    should_continue=False,
                    next_node=fail_route,
                    terminal=False,
                    error_message=""
                )
            else:
                # No fail_route defined - terminate session
                logger.warning(
                    f"Max validation attempts reached, terminating session (no fail_route)",
                    attempts=new_attempt_count,
                    max_attempts=max_attempts
                )
                await self.session_manager.error_session(session.session_id)
                return RetryResult(
                    should_continue=False,
                    next_node=None,
                    terminal=True,
                    error_message=""
                )

        # Not at max attempts yet - continue with retry
        final_error_message = error_message

        # Render counter text if defined
        # Use render_counter() method which allows {{current_attempt}} and {{max_attempts}}
        if counter_text:
            counter_context = {
                **context,
                'current_attempt': new_attempt_count,
                'max_attempts': max_attempts
            }
            rendered_counter = self.template_engine.render_counter(counter_text, counter_context)
            final_error_message = f"{error_message}\n{rendered_counter}"

        return RetryResult(
            should_continue=True,
            next_node=None,
            terminal=False,
            error_message=final_error_message
        )

    async def reset_attempts(self, session: Any) -> None:
        """
        Reset validation attempts counter

        Args:
            session: Current session object

        Note:
            Called when:
            - Validation succeeds
            - Interrupt is triggered
            - Max attempts reached
        """
        await self.session_manager.reset_validation_attempts(session.session_id)
