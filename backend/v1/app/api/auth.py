"""
Authentication API
Endpoints for user registration, login, and profile management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User
from app.schemas.auth_schema import (
    UserCreate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    Token
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
from app.utils.exceptions import AuthenticationError

security = HTTPBearer()

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    if settings.redis.enabled and redis_manager.is_connected():
        client_ip = request.client.host if request.client else "unknown"

        # Rate limit registrations per IP
        rate_key = f"register:{client_ip}"
        allowed = await redis_manager.check_rate_limit_user(
            rate_key,
            max_requests=settings.rate_limit.register_max,
            window_seconds=settings.rate_limit.register_window
        )
        
        if not allowed:
            logger.warning(f"Registration rate limit exceeded", ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )
    
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password (validates length constraints)
    try:
        hashed_password = get_password_hash(user_data.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
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
        
        return user
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e)
        if "email" in error_msg or "users_email_key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            logger.error(f"Registration failed with integrity error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    User login
    
    Args:
        credentials: Login credentials (email and password)
        request: HTTP request (for IP-based rate limiting)
        db: Database session
    
    Returns:
        Access token and user profile
    
    Raises:
        HTTPException: If credentials are invalid or rate limit exceeded
    """
    # Rate limit login attempts by IP address to prevent brute-force attacks
    if settings.redis.enabled and redis_manager.is_connected():
        client_ip = request.client.host if request.client else "unknown"

        # Rate limit login attempts per IP
        rate_key = f"login:{client_ip}"
        allowed = await redis_manager.check_rate_limit_user(
            rate_key,
            max_requests=settings.rate_limit.login_max,
            window_seconds=settings.rate_limit.login_window
        )
        
        if not allowed:
            logger.warning(f"Login rate limit exceeded", ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
    
    # Get user by email
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"Login failed - user not found", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Login failed - invalid password", user_id=str(user.user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token (convert UUID to string for JWT)
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=settings.security.access_token_expire_minutes)
    )

    logger.info(f"User logged in", user_id=str(user.user_id))

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """
    User logout - Blacklist current JWT token
    
    Args:
        credentials: JWT token from Authorization header
        current_user: Current authenticated user
    
    Returns:
        Logout confirmation message
    
    Note:
        - Token is added to blacklist if Redis is enabled
        - Token remains invalid until it expires naturally
        - If Redis is not available, logout only logs the action
    """
    token = credentials.credentials

    # Blacklist token if Redis is enabled
    if settings.redis.enabled and redis_manager.is_connected():
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
        logger.info(f"User logged out (Redis disabled)", user_id=str(current_user.user_id))
    
    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.user_id)
    }