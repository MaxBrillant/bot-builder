"""
API Middleware
Consolidated middleware for ownership checking and exception handling

Eliminates duplicate ownership verification code across API endpoints
and provides consistent error responses via exception handlers.
"""

from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bot_service import BotService
from app.services.flow_service import FlowService
from app.models.bot import Bot
from app.models.flow import Flow
from app.models.user import User
from app.utils.logger import get_logger
from app.utils.exceptions import (
    BotBuilderException,
    SystemException,
    ValidationException,
    SessionException,
    ExecutionException,
    AuthenticationException,
    ResourceNotFoundException,
    BotNotFoundError,
    FlowNotFoundError,
    SessionExpiredError,
    SessionNotFoundError,
    UnauthorizedError
)

logger = get_logger(__name__)


# ===== Ownership Verification =====
class OwnershipChecker:
    """
    Reusable ownership verification for API endpoints

    Eliminates ~12 instances of duplicate ownership checking code
    across flows.py, bots.py, and webhooks.py.

    Usage:
        checker = OwnershipChecker(db)
        bot = await checker.verify_bot_ownership(bot_id, current_user.user_id)
        flow = await checker.verify_flow_ownership(flow_id, current_user.user_id)
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize ownership checker

        Args:
            db: Database session
        """
        self.db = db
        self.bot_service = BotService(db)
        self.flow_service = FlowService(db)

    async def verify_bot_ownership(
        self,
        bot_id: UUID,
        user_id: UUID,
        allow_missing: bool = False
    ) -> Optional[Bot]:
        """
        Verify user owns the specified bot

        Args:
            bot_id: Bot UUID
            user_id: User UUID
            allow_missing: If True, return None instead of raising HTTPException

        Returns:
            Bot instance if ownership verified

        Raises:
            HTTPException: 404 if bot not found, 403 if not owner
        """
        try:
            bot = await self.bot_service.get_bot(
                bot_id,
                owner_user_id=user_id,
                check_ownership=True
            )

            if not bot:
                if allow_missing:
                    return None
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Bot '{bot_id}' not found"
                )

            return bot

        except BotNotFoundError as e:
            if allow_missing:
                return None
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except UnauthorizedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to access bot '{bot_id}'"
            )

    async def verify_flow_ownership(
        self,
        flow_id: UUID,
        user_id: UUID,
        allow_missing: bool = False
    ) -> Optional[Flow]:
        """
        Verify user owns the bot that owns the specified flow

        Args:
            flow_id: Flow UUID
            user_id: User UUID
            allow_missing: If True, return None instead of raising HTTPException

        Returns:
            Flow instance if ownership verified

        Raises:
            HTTPException: 404 if flow not found, 403 if not owner
        """
        try:
            flow = await self.flow_service.get_flow(flow_id)

            if not flow:
                if allow_missing:
                    return None
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Flow '{flow_id}' not found"
                )

            # Verify bot ownership (flow -> bot -> user)
            bot = await self.bot_service.get_bot(
                flow.bot_id,
                owner_user_id=user_id,
                check_ownership=True
            )

            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You don't have permission to access flow '{flow_id}'"
                )

            return flow

        except FlowNotFoundError as e:
            if allow_missing:
                return None
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except (BotNotFoundError, UnauthorizedError) as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to access flow '{flow_id}'"
            )

    async def verify_bot_and_flow_ownership(
        self,
        bot_id: UUID,
        flow_id: UUID,
        user_id: UUID
    ) -> tuple[Bot, Flow]:
        """
        Verify user owns both bot and flow, and that flow belongs to bot

        Args:
            bot_id: Bot UUID
            flow_id: Flow UUID
            user_id: User UUID

        Returns:
            Tuple of (Bot, Flow) if all checks pass

        Raises:
            HTTPException: 404 if not found, 403 if not owner, 400 if flow doesn't belong to bot
        """
        # Verify bot ownership
        bot = await self.verify_bot_ownership(bot_id, user_id)

        # Verify flow ownership
        flow = await self.verify_flow_ownership(flow_id, user_id)

        # Verify flow belongs to bot
        if flow.bot_id != bot_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flow '{flow_id}' does not belong to bot '{bot_id}'"
            )

        return bot, flow


# ===== Global Exception Handlers =====

async def validation_exception_handler(
    request: Request,
    exc: ValidationException
) -> JSONResponse:
    """
    Handle validation exceptions

    Returns:
        400 Bad Request with validation errors
    """
    logger.warning(
        f"Validation error: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        metadata=exc.metadata
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "errors": exc.metadata.get('errors', []) if exc.metadata else []
        }
    )


async def session_exception_handler(
    request: Request,
    exc: SessionException
) -> JSONResponse:
    """
    Handle session exceptions

    Returns:
        410 Gone for expired sessions, 404 for not found
    """
    # Map specific exceptions to status codes
    status_code_map = {
        SessionExpiredError: status.HTTP_410_GONE,
        SessionNotFoundError: status.HTTP_404_NOT_FOUND
    }

    status_code = status_code_map.get(
        type(exc),
        status.HTTP_400_BAD_REQUEST  # Default for other session errors
    )

    logger.warning(
        f"Session error: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        status_code=status_code
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code
        }
    )


async def execution_exception_handler(
    request: Request,
    exc: ExecutionException
) -> JSONResponse:
    """
    Handle execution exceptions (flow runtime errors)

    Returns:
        500 Internal Server Error
    """
    logger.error(
        f"Execution error: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        metadata=exc.metadata
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Flow execution error",
            "error_code": exc.error_code,
            "details": exc.message
        }
    )


async def system_exception_handler(
    request: Request,
    exc: SystemException
) -> JSONResponse:
    """
    Handle system/infrastructure exceptions

    Returns:
        503 Service Unavailable
    """
    logger.error(
        f"System error: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        metadata=exc.metadata
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Service temporarily unavailable",
            "error_code": exc.error_code
        }
    )


async def authentication_exception_handler(
    request: Request,
    exc: AuthenticationException
) -> JSONResponse:
    """
    Handle authentication exceptions

    Returns:
        401 Unauthorized
    """
    logger.warning(
        f"Authentication error: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": exc.message,
            "error_code": exc.error_code
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def resource_not_found_exception_handler(
    request: Request,
    exc: ResourceNotFoundException
) -> JSONResponse:
    """
    Handle resource not found exceptions

    Returns:
        404 Not Found
    """
    logger.info(
        f"Resource not found: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        metadata=exc.metadata
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": exc.message,
            "error_code": exc.error_code
        }
    )


async def generic_botbuilder_exception_handler(
    request: Request,
    exc: BotBuilderException
) -> JSONResponse:
    """
    Handle all other BotBuilderException subclasses

    Returns:
        500 Internal Server Error (catch-all)
    """
    logger.error(
        f"Unhandled BotBuilder exception: {exc.message}",
        path=str(request.url),
        error_code=exc.error_code,
        exception_type=type(exc).__name__,
        metadata=exc.metadata
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An internal error occurred",
            "error_code": exc.error_code
        }
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with user-friendly messages

    Returns:
        422 Unprocessable Entity with detailed validation errors
    """
    errors = []
    for error in exc.errors():
        # Extract field path
        loc = error.get("loc", [])
        # Skip 'body' prefix if present
        field_path = ".".join(str(x) for x in loc if x != "body")

        # Get error message
        msg = error.get("msg", "Validation error")

        # Format user-friendly error message
        if field_path:
            errors.append(f"{field_path}: {msg}")
        else:
            errors.append(msg)

    # Combine all errors into a single message
    error_message = "; ".join(errors) if errors else "Validation error occurred"

    logger.warning(
        f"Request validation error: {error_message}",
        path=str(request.url),
        errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": error_message,
            "errors": errors
        }
    )


# ===== Registration Helper =====
def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app

    Usage:
        from app.api.middleware import register_exception_handlers
        register_exception_handlers(app)

    Args:
        app: FastAPI application instance
    """
    # FastAPI/Pydantic validation errors
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    # Category handlers (most specific first)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(SessionException, session_exception_handler)
    app.add_exception_handler(ExecutionException, execution_exception_handler)
    app.add_exception_handler(SystemException, system_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_exception_handler)

    # Generic catch-all for any BotBuilderException not handled above
    app.add_exception_handler(BotBuilderException, generic_botbuilder_exception_handler)

    logger.info("Registered exception handlers for all BotBuilderException categories and RequestValidationError")
