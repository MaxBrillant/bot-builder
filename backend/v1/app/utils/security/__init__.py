"""
Security Utilities
JWT token generation, password hashing, input sanitization, and SSRF protection
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

from jose import JWTError, jwt

from app.config import settings
from app.utils.exceptions import AuthenticationError

# Re-exports from submodules
from .password import verify_password, get_password_hash
from .sanitization import sanitize_input, check_suspicious_patterns, escape_html, SanitizationError
from .ssrf import is_safe_url_for_ssrf, validate_node_id_format, generate_session_id, BLOCKED_IP_NETWORKS


# JWT Functions (kept in __init__.py as they're small and tightly coupled to auth)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with JTI (JWT ID) for token blacklisting

    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token with JTI claim
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.security.access_token_expire_minutes)

    # Add expiration and unique JWT ID for blacklisting
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  # Unique token identifier for blacklist
    })
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT access token

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.security.secret_key, algorithms=[settings.security.algorithm])
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def extract_user_id_from_token(token: str) -> str:
    """
    Extract user_id from JWT token as string

    Args:
        token: JWT token

    Returns:
        User ID from token as string (UUID representation)

    Raises:
        AuthenticationError: If token is invalid or doesn't contain user_id

    Note:
        JWT tokens store UUID as string. This must be converted to UUID
        when querying the database.
    """
    payload = decode_access_token(token)
    user_id: Optional[str] = payload.get("sub")

    if user_id is None:
        raise AuthenticationError("Token does not contain user ID")

    return user_id


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token (longer expiration)

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Refresh tokens expire after 7 days by default
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.security.secret_key, algorithm=settings.security.algorithm)

    return encoded_jwt


__all__ = [
    # JWT functions
    'create_access_token',
    'decode_access_token',
    'extract_user_id_from_token',
    'create_refresh_token',
    # Password functions
    'verify_password',
    'get_password_hash',
    # Sanitization functions
    'sanitize_input',
    'check_suspicious_patterns',
    'escape_html',
    'SanitizationError',
    # SSRF protection and utilities
    'is_safe_url_for_ssrf',
    'validate_node_id_format',
    'generate_session_id',
    'BLOCKED_IP_NETWORKS',
]
