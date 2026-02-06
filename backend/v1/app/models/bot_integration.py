"""
Bot Integration Model
Stores platform-specific integration configurations separate from core Bot model
Config is encrypted at rest since it contains API tokens and secrets.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
import uuid

from app.database import Base
from app.utils.constants import IntegrationPlatform, IntegrationStatus


class BotIntegration(Base):
    """
    Platform-specific integration configuration

    Maintains platform-agnostic design by isolating platform data from core Bot model.
    Each bot can have multiple integrations (one per platform).
    """

    __tablename__ = "bot_integrations"

    integration_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.bot_id", ondelete="CASCADE"), nullable=False, index=True)

    # Platform: stored as string, validated by application enum and DB constraint
    # Uses String column to avoid SQLAlchemy enum NAME vs VALUE confusion
    platform = Column(String(50), nullable=False, index=True)

    # ENCRYPTED: Platform-specific config (contains API tokens and secrets)
    # WhatsApp: {"instance_name": "bot_abc", "phone_number": "+254..."}
    # Telegram: {"bot_token": "...", "chat_id": "..."}
    # Slack: {"workspace_id": "...", "bot_user_id": "..."}
    _config_encrypted = Column("config", LargeBinary, nullable=False)

    # Status: connected, disconnected, connecting, error
    status = Column(String(20), nullable=False, default=IntegrationStatus.DISCONNECTED.value, index=True)

    # Connection tracking
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("platform IN ('WHATSAPP', 'TELEGRAM', 'SLACK')", name='check_integration_platform'),
        CheckConstraint("status IN ('CONNECTED', 'DISCONNECTED', 'CONNECTING', 'ERROR')", name='check_integration_status'),
        # One integration per bot per platform
        Index('idx_unique_bot_platform', 'bot_id', 'platform', unique=True),
    )

    # Relationships
    bot = relationship("Bot", back_populates="integrations")

    # Hybrid property for transparent encryption/decryption of config
    @hybrid_property
    def config(self) -> dict:
        """Decrypt and return config"""
        from app.utils.encryption import get_encryption_service
        encrypted = self.__dict__.get('_config_encrypted')
        if not isinstance(encrypted, (bytes, str)):
            return {}  # Not yet initialized
        encryption = get_encryption_service()
        decrypted = encryption.decrypt_json(encrypted)
        return decrypted if decrypted is not None else {}

    @config.setter
    def config(self, value: dict):
        """Encrypt and store config"""
        from app.utils.encryption import get_encryption_service
        encryption = get_encryption_service()
        self._config_encrypted = encryption.encrypt_json(value if value else {})

    def __repr__(self):
        return f"<BotIntegration(bot_id='{self.bot_id}', platform='{self.platform}', status='{self.status}')>"

    def to_dict(self, include_config: bool = False):
        """Convert to dict (config excluded by default for security)"""
        result = {
            "integration_id": str(self.integration_id),
            "bot_id": str(self.bot_id),
            "platform": self.platform.value if isinstance(self.platform, IntegrationPlatform) else self.platform,
            "status": self.status,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_config:
            result["config"] = self.config

        return result
