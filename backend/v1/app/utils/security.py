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

    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=settings.security.bcrypt_rounds))
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


def sanitize_input(text: str) -> tuple[str, dict]:
    """
    Layer 1: Baseline Sanitization (Universal, Always Applied)

    Removes dangerous characters and enforces length limits per spec Section 10.1.

    Args:
        text: Raw user input text

    Returns:
        Tuple of (sanitized_text, sanitization_metadata)

    Sanitization metadata contains:
        - original_length: Original text length
        - sanitized_length: Final text length
        - null_bytes_removed: Count of null bytes removed
        - control_chars_removed: Count of control characters removed
        - was_truncated: Whether text was truncated to 4096 chars

    Operations:
        1. Remove null bytes (\x00)
        2. Remove control characters (except \n, \t, \r)
        3. Trim leading/trailing whitespace
        4. Truncate to 4096 characters maximum

    Note:
        This is Layer 1 of the 3-layer sanitization system.
        Layer 2 (context-aware escaping) happens at point of use.
        Layer 3 (pattern rejection) is checked separately via check_suspicious_patterns().
    """
    original_length = len(text)
    null_bytes_removed = 0
    control_chars_removed = 0

    # 1. Remove null bytes
    if '\x00' in text:
        null_bytes_removed = text.count('\x00')
        text = text.replace('\x00', '')

    # 2. Remove control characters (except newline, tab, carriage return)
    cleaned_chars = []
    for char in text:
        char_code = ord(char)
        # Keep printable chars, newline (\n = 10), tab (\t = 9), carriage return (\r = 13)
        if char in '\n\t\r' or char_code >= 32:
            cleaned_chars.append(char)
        else:
            control_chars_removed += 1

    text = ''.join(cleaned_chars)

    # 3. Trim whitespace
    text = text.strip()

    # 4. Enforce length limit (4096 characters)
    was_truncated = False
    if len(text) > 4096:
        text = text[:4096]
        was_truncated = True

    sanitized_length = len(text)

    metadata = {
        'original_length': original_length,
        'sanitized_length': sanitized_length,
        'null_bytes_removed': null_bytes_removed,
        'control_chars_removed': control_chars_removed,
        'was_truncated': was_truncated
    }

    return text, metadata


def check_suspicious_patterns(text: str) -> tuple[bool, Optional[str]]:
    """
    Layer 3: Pattern Rejection (Universal, Always Applied)

    Detects dangerous patterns that indicate attack attempts per spec Section 10.1.

    Args:
        text: User input text (after Layer 1 sanitization)

    Returns:
        Tuple of (is_safe, pattern_type)
        - is_safe: True if no suspicious patterns found, False otherwise
        - pattern_type: Type of pattern detected (None if safe)

    Detected Patterns:
        - Script tags: <script>, </script>
        - JavaScript protocols: javascript:
        - Event handlers: onclick=, onerror=, onload=
        - Template injection: {{, }}, ${, }
        - Command injection: ;, |, &&
        - Path traversal: ../, ..\\
        - SQL comments: --, /*, */

    Note:
        This is Layer 3 of the 3-layer sanitization system.
        When suspicious pattern detected, input is rejected with error message.
    """
    # Patterns that indicate attack attempts
    patterns = [
        (r'<script[^>]*>', 'script_tag'),
        (r'</script>', 'script_tag'),
        (r'javascript:', 'javascript_protocol'),
        (r'on\w+\s*=', 'event_handler'),  # onclick=, onerror=, etc.
        (r'\{\{', 'template_injection'),
        (r'\}\}', 'template_injection'),
        (r'\$\{', 'template_injection'),
        (r'\}', 'template_injection_closing'),  # Check for ${...} pattern
        (r';\s*\w+', 'command_injection'),  # ; followed by command
        (r'\|\|', 'command_injection'),
        (r'&&', 'command_injection'),
        (r'\|', 'command_injection'),
        (r'\.\./|\.\.\\', 'path_traversal'),
        (r'--', 'sql_comment'),
        (r'/\*', 'sql_comment'),
        (r'\*/', 'sql_comment'),
    ]

    for pattern, pattern_type in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, pattern_type

    return True, None


def escape_html(text: str) -> str:
    """
    Layer 2: Context-Aware Escaping - HTML

    Escapes HTML special characters to prevent XSS attacks.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text

    Escapes:
        < → &lt;
        > → &gt;
        & → &amp;
        " → &quot;
        ' → &#x27;

    Note:
        This is part of Layer 2 (context-aware escaping).
        Called when rendering content in web interfaces.
    """
    return (text
            .replace('&', '&amp;')  # Must be first
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


class SanitizationError(Exception):
    """
    Raised when input fails sanitization checks (Layer 3 pattern rejection)

    Attributes:
        message: User-facing error message
        pattern_type: Type of suspicious pattern detected
        original_input_length: Length of original input (for logging)
    """
    def __init__(self, message: str, pattern_type: str, original_input_length: int):
        super().__init__(message)
        self.message = message
        self.pattern_type = pattern_type
        self.original_input_length = original_input_length


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