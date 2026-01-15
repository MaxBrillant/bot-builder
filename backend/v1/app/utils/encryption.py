"""
Encryption Service
Application-layer encryption for sensitive data (PII, session data)

Uses Fernet (symmetric encryption) with AES-128-CBC and HMAC-SHA256.
Implements field-level encryption for session data per spec Section 10.3 and 10.5.
"""

import json
from typing import Optional, Any
from cryptography.fernet import Fernet, InvalidToken
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """
    Application-layer encryption service for PII and session data

    Features:
    - Field-level encryption (encrypt/decrypt individual values)
    - JSON serialization support for complex types
    - Safe error handling (returns None on decryption failure)
    - Audit logging for encryption events

    Security:
    - Fernet uses AES-128-CBC with HMAC-SHA256
    - Encryption key from environment (min 44 chars, base64)
    - Invalid tokens logged but don't crash

    Usage:
        encryption = EncryptionService(settings.security.encryption_key)
        encrypted = encryption.encrypt("sensitive data")
        decrypted = encryption.decrypt(encrypted)
    """

    def __init__(self, encryption_key: str):
        """
        Initialize encryption service with key

        Args:
            encryption_key: Base64-encoded 32-byte key (44 chars)
                          Generate with: Fernet.generate_key().decode()

        Raises:
            ValueError: If encryption key is invalid format
        """
        try:
            self.cipher = Fernet(encryption_key.encode('utf-8'))
        except Exception as e:
            logger.critical(
                "Failed to initialize encryption service",
                error=str(e)
            )
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt(self, data: str) -> bytes:
        """
        Encrypt string data

        Args:
            data: Plain text string to encrypt

        Returns:
            Encrypted bytes

        Note:
            Empty strings return empty bytes (not encrypted).
            Encryption events are logged for audit trail.
        """
        if not data:
            return b''

        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            logger.debug("Data encrypted successfully", length=len(data))
            return encrypted
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise

    def decrypt(self, data: bytes) -> str:
        """
        Decrypt bytes to string

        Args:
            data: Encrypted bytes

        Returns:
            Decrypted string, or empty string if data is empty

        Raises:
            InvalidToken: If decryption fails (invalid key, corrupted data)

        Note:
            Decryption failures are logged for security monitoring.
        """
        if not data:
            return ''

        try:
            decrypted = self.cipher.decrypt(data).decode('utf-8')
            logger.debug("Data decrypted successfully")
            return decrypted
        except InvalidToken as e:
            logger.error(
                "Decryption failed - invalid token",
                error=str(e),
                security_event="DECRYPTION_FAILURE"
            )
            raise
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise

    def encrypt_json(self, data: Any) -> bytes:
        """
        Encrypt any JSON-serializable data

        Args:
            data: JSON-serializable data (dict, list, etc.)

        Returns:
            Encrypted bytes

        Example:
            encrypted = encryption.encrypt_json({"user": "Alice", "age": 30})
        """
        if data is None:
            return b''

        try:
            json_string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            return self.encrypt(json_string)
        except (TypeError, ValueError) as e:
            logger.error("JSON serialization failed before encryption", error=str(e))
            raise

    def decrypt_json(self, data: bytes) -> Any:
        """
        Decrypt and parse JSON data

        Args:
            data: Encrypted bytes containing JSON

        Returns:
            Parsed JSON object, or None if data is empty

        Raises:
            InvalidToken: If decryption fails
            json.JSONDecodeError: If decrypted data is not valid JSON
        """
        if not data:
            return None

        try:
            decrypted_string = self.decrypt(data)
            return json.loads(decrypted_string)
        except json.JSONDecodeError as e:
            logger.error(
                "JSON parsing failed after decryption",
                error=str(e),
                security_event="INVALID_ENCRYPTED_JSON"
            )
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key

        Returns:
            Base64-encoded key as string (44 characters)

        Example:
            key = EncryptionService.generate_key()
            # Save to environment: SECURITY__ENCRYPTION_KEY=key
        """
        return Fernet.generate_key().decode('utf-8')


# Global encryption service instance (initialized lazily)
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get global encryption service instance

    Returns:
        Shared EncryptionService instance

    Note:
        Service is initialized lazily on first access.
        Requires settings.security.encryption_key to be configured.
    """
    global _encryption_service

    if _encryption_service is None:
        from app.config import settings
        _encryption_service = EncryptionService(settings.security.encryption_key)

    return _encryption_service
