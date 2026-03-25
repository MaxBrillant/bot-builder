"""
Password Hashing and Verification
"""

import bcrypt

from app.config import settings


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
