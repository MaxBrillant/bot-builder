"""
Security Utilities
JWT token generation, password hashing, and authentication helpers
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid
import re
import bcrypt
from jose import JWTError, jwt

from app.config import settings
from app.utils.exceptions import AuthenticationError


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    
    Note:
        bcrypt has a 72-byte limit. Passwords are validated during registration
        to ensure they fit within this limit.
    """
    password_bytes = plain_password.encode('utf-8')
    
    # Bcrypt will use first 72 bytes automatically, but we validate on registration
    # so this shouldn't be an issue for new passwords
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    
    Raises:
        ValueError: If password is too long (>72 characters or >72 bytes)
    
    Note:
        bcrypt has a 72-byte password limit. We validate and reject passwords
        that exceed this limit to prevent silent truncation and user confusion.
    """
    # Validate password length (character count)
    if len(password) > 72:
        raise ValueError("Password too long (maximum 72 characters)")
    
    # Validate password byte length (for multi-byte characters)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError(
            "Password contains too many bytes (maximum 72 bytes). "
            "Try using fewer special characters or emojis."
        )
    
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS))
    return hashed.decode('utf-8')


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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration and unique JWT ID for blacklisting
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  # Unique token identifier for blacklist
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by trimming whitespace
    
    Args:
        text: Input text to sanitize
    
    Returns:
        Sanitized text
    
    Note:
        As per specification, system automatically trims leading/trailing whitespace.
        No automatic HTML/SQL injection prevention - developer must validate appropriately.
    """
    return text.strip()


def validate_flow_id_format(flow_id: str) -> bool:
    """
    Validate flow_id format
    
    Args:
        flow_id: Flow identifier
    
    Returns:
        True if valid format, False otherwise
    
    Rules:
        - Alphanumeric and underscores only
        - No spaces
        - Length <= 96 characters
    """
    if not flow_id or len(flow_id) > 96:
        return False
    
    return bool(re.match(r'^[A-Za-z0-9_]+$', flow_id))


def validate_node_id_format(node_id: str) -> bool:
    """
    Validate node_id format
    
    Args:
        node_id: Node identifier
    
    Returns:
        True if valid format, False otherwise
    
    Rules:
        - Alphanumeric and underscores only
        - No spaces
        - Length <= 96 characters
    """
    if not node_id or len(node_id) > 96:
        return False
    
    return bool(re.match(r'^[A-Za-z0-9_]+$', node_id))


def generate_session_id() -> str:
    """
    Generate a unique session ID
    
    Returns:
        UUID string for session
    """
    return str(uuid.uuid4())