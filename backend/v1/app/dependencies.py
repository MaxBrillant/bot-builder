"""
Dependency Injection Functions
JWT authentication and rate limiting dependencies

SECURITY: Authentication is via httpOnly cookies ONLY.
This prevents XSS attacks from stealing tokens via JavaScript.
"""

from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import extract_user_id_from_token
from app.utils.exceptions import AuthenticationError, SecurityServiceUnavailableError
from app.core.redis_manager import redis_manager
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cookie name for access token (must match auth.py and oauth.py)
ACCESS_TOKEN_COOKIE_NAME = "access_token"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user

    SECURITY: Only checks httpOnly cookie for JWT token.
    This is more secure than Authorization headers because:
    - httpOnly cookies cannot be accessed by JavaScript (XSS protection)
    - Cookies are automatically sent with requests (no localStorage needed)

    Args:
        request: HTTP request (for cookie access)
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # SECURITY: Only accept token from httpOnly cookie
        token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

        if not token:
            raise AuthenticationError("No authentication token provided")

        # Extract user_id and JTI from token
        user_id = extract_user_id_from_token(token)

        # Check if token is blacklisted by JTI
        if not redis_manager.is_connected():
            raise AuthenticationError("Authentication service unavailable")

        # Decode token to get JTI
        from app.utils.security import decode_access_token
        payload = decode_access_token(token)
        jti = payload.get("jti")

        if jti:
            is_blacklisted = await redis_manager.is_token_blacklisted(jti)
            if is_blacklisted:
                raise AuthenticationError("Token has been revoked")

        # Get user from database using repository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(user_id))

        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Check user rate limit
        if redis_manager.is_connected():
            allowed = await redis_manager.check_rate_limit_user(
                user_id,
                settings.rate_limit.user_max,
                settings.rate_limit.user_window
            )
            if not allowed:
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except SecurityServiceUnavailableError as e:
        # SECURITY: If Redis is down, we can't verify token blacklist or rate limit
        logger.error(f"Security service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again later.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

