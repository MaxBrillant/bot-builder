"""
Authentication API
Endpoints for user registration, login, and profile management

SECURITY: Authentication is via httpOnly cookies ONLY.
This prevents XSS attacks from stealing tokens via JavaScript.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditResult
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.auth_schema import (
    UserCreate,
    UserResponse,
    LoginRequest,
    LoginResponse,
)
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.dependencies import get_current_user
from app.config import settings
from app.core.redis_manager import redis_manager
from app.utils.logger import get_logger
from app.utils.exceptions import AuthenticationError, SecurityServiceUnavailableError
from app.utils.responses import (
    too_many_requests,
    service_unavailable,
    bad_request,
    unauthorized,
    forbidden,
    internal_server_error
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie configuration
ACCESS_TOKEN_COOKIE_NAME = "access_token"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    Args:
        user_data: User registration data
        request: HTTP request (for IP-based rate limiting)
        db: Database session
    
    Returns:
        Created user profile
    
    Raises:
        HTTPException: If user_id or email already exists, or rate limit exceeded
    """
    # Rate limit registration by IP address
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"register:{client_ip}"
    try:
        allowed = await redis_manager.check_rate_limit_user(
            rate_key,
            max_requests=settings.rate_limit.register_max,
            window_seconds=settings.rate_limit.register_window
        )

        if not allowed:
            logger.warning(f"Registration rate limit exceeded", ip=client_ip)
            raise too_many_requests("Too many registration attempts. Please try again later.")
    except SecurityServiceUnavailableError:
        # SECURITY: If Redis is down, we can't rate limit - reject registration for safety
        logger.error("Redis unavailable during registration - rejecting for security")
        raise service_unavailable("Registration service temporarily unavailable. Please try again later.")
    
    # Check if email already exists
    stmt = select(User).where(func.lower(User.email) == func.lower(user_data.email))
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise bad_request("Email already registered")
    
    # Hash password (validates length constraints)
    try:
        hashed_password = get_password_hash(user_data.password)
    except ValueError as e:
        raise bad_request(str(e))
    
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        is_active=True
    )
    
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"User registered", user_id=str(user.user_id), email=user.email)

        # Create example bot with flows for new user
        from app.services.bot_service import BotService
        bot_service = BotService(db)
        await bot_service.create_example_bot_for_user(user.user_id)

        return user
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e)
        if "email" in error_msg or "users_email_key" in error_msg or "idx_users_email_unique_lower" in error_msg:
            raise bad_request("Email already registered")
        else:
            logger.error(f"Registration failed with integrity error: {error_msg}")
            raise bad_request("Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    User login

    Args:
        credentials: Login credentials (email and password)
        request: HTTP request (for IP-based rate limiting)
        response: HTTP response (for setting cookies)
        db: Database session

    Returns:
        User profile (token is set via httpOnly cookie, not in response body)

    Security:
        SECURITY: Token is set via httpOnly cookie ONLY.
        This prevents XSS attacks from stealing tokens via JavaScript.
        Token is NOT returned in response body.

    Raises:
        HTTPException: If credentials are invalid or rate limit exceeded
    """
    # Rate limit login attempts by IP address to prevent brute-force attacks
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}"
    try:
        allowed = await redis_manager.check_rate_limit_user(
            rate_key,
            max_requests=settings.rate_limit.login_max,
            window_seconds=settings.rate_limit.login_window
        )

        if not allowed:
            logger.warning(f"Login rate limit exceeded", ip=client_ip)
            raise too_many_requests("Too many login attempts. Please try again later.")
    except SecurityServiceUnavailableError:
        # SECURITY: If Redis is down, we can't rate limit - reject login for safety
        logger.error("Redis unavailable during login - rejecting for security")
        raise service_unavailable("Authentication service temporarily unavailable. Please try again later.")

    # Get user by email
    stmt = select(User).where(func.lower(User.email) == func.lower(credentials.email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login failed - user not found", email=credentials.email)
        raise unauthorized("Incorrect email or password")

    # Check if user is OAuth-only (no password set)
    if not user.password_hash:
        logger.warning(f"Login failed - OAuth-only user attempted password login", user_id=str(user.user_id))
        raise bad_request("This account uses Google Sign-In. Please use the 'Sign in with Google' button.")

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Login failed - invalid password", user_id=str(user.user_id))
        raise unauthorized("Incorrect email or password")

    # Check if user is active
    if not user.is_active:
        raise forbidden("User account is inactive")

    # Create access token (convert UUID to string for JWT)
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=settings.security.access_token_expire_minutes)
    )

    # SECURITY: Set token as httpOnly cookie ONLY (not in response body)
    # This prevents XSS attacks from stealing tokens via JavaScript
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,              # JavaScript cannot access this cookie
        secure=settings.is_production,  # HTTPS only in production
        samesite="lax",             # CSRF protection
        max_age=settings.security.access_token_expire_minutes * 60,
        path="/"
    )

    logger.info(f"User logged in", user_id=str(user.user_id))

    # Return user data only (token is in httpOnly cookie)
    return LoginResponse(
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user profile
    
    Args:
        current_user: Current authenticated user (from token)
    
    Returns:
        User profile
    """
    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    User logout - Blacklist current JWT token and clear cookie

    Args:
        request: HTTP request (for cookie access)
        response: HTTP response (for clearing cookie)
        current_user: Current authenticated user

    Returns:
        Logout confirmation message

    Note:
        - Token is added to blacklist via Redis
        - Token remains invalid until it expires naturally
        - Cookie is always cleared
    """
    # Get token from httpOnly cookie
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    # Always clear the cookie
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax"
    )

    # Blacklist token if available
    if token:
        try:
            # Decode token to get JTI and expiration time
            payload = decode_access_token(token)
            jti = payload.get("jti")
            exp_timestamp = payload.get("exp")

            if not jti:
                logger.error(f"Token missing JTI claim", user_id=str(current_user.user_id))
            elif exp_timestamp:
                # Calculate TTL (time to live) for blacklist entry
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                ttl_seconds = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())

                if ttl_seconds > 0:
                    # Blacklist token by JTI with TTL matching token expiration
                    await redis_manager.blacklist_token(jti, ttl_seconds)
                    logger.info(f"Token blacklisted", user_id=str(current_user.user_id), jti=jti[:8])
                else:
                    logger.warning(f"Token already expired", user_id=str(current_user.user_id))
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}", user_id=str(current_user.user_id))
            # Don't fail logout if blacklist fails
    else:
        logger.info(f"User logged out (no token to blacklist)", user_id=str(current_user.user_id))

    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.user_id)
    }


@router.delete("/me/data", status_code=status.HTTP_200_OK)
async def delete_user_data(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all user data (GDPR "Right to be Forgotten")

    This endpoint permanently deletes:
    - User account
    - All bots owned by the user
    - All flows in those bots
    - All sessions associated with those bots
    - All bot integrations

    Args:
        request: HTTP request (for cookie access)
        response: HTTP response (for clearing cookie)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Confirmation message

    Warning:
        This action is IRREVERSIBLE. All data will be permanently deleted.

    Security:
        - Requires authentication
        - Audit logs the deletion event (with masked PII)
        - Token is blacklisted after deletion
        - Cookie is always cleared
    """
    user_id = str(current_user.user_id)
    user_email = current_user.email

    # Audit log: data deletion request (before deletion)
    audit_log = AuditLogRepository(db)
    await audit_log.log_security_event(
        action="user_data_deletion_requested",
        user_id=logger.mask_pii(user_email, "email"),
        result=AuditResult.SUCCESS,
        event_metadata={
            "user_id_hash": user_id[:8] + "...",  # Partial ID for audit trail
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    try:
        # Delete user (cascades to bots, flows, sessions, integrations)
        await db.delete(current_user)
        await db.commit()

        logger.info(
            f"User data deleted (GDPR request)",
            user_id_partial=user_id[:8] + "..."
        )

        # Get token from httpOnly cookie
        token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

        # Clear the authentication cookie
        response.delete_cookie(
            key=ACCESS_TOKEN_COOKIE_NAME,
            path="/",
            httponly=True,
            secure=settings.is_production,
            samesite="lax"
        )

        # Blacklist the current token
        if token and redis_manager.is_connected():
            try:
                payload = decode_access_token(token)
                jti = payload.get("jti")
                exp_timestamp = payload.get("exp")

                if jti and exp_timestamp:
                    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    ttl_seconds = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())

                    if ttl_seconds > 0:
                        await redis_manager.blacklist_token(jti, ttl_seconds)
            except Exception as e:
                # Don't fail deletion if token blacklist fails
                logger.warning(f"Failed to blacklist token after deletion: {e}")

        return {
            "message": "All user data has been permanently deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user data: {str(e)}", user_id_partial=user_id[:8])

        # Audit log: deletion failure
        await audit_log.log_security_event(
            action="user_data_deletion_failed",
            user_id=logger.mask_pii(user_email, "email"),
            result=AuditResult.FAILED,
            event_metadata={"error": str(e)[:100]}  # Truncate error for audit
        )

        raise internal_server_error("Failed to delete user data. Please try again or contact support.")