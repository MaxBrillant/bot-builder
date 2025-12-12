"""
Configuration Management
Loads settings from environment variables using Pydantic
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, Field
from typing import List
import warnings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://botbuilder:password@localhost:5432/botbuilder"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    
    # Rate Limiting
    RATE_LIMIT_WEBHOOK_MAX: int = 10  # Max webhook requests per channel user per minute
    RATE_LIMIT_WEBHOOK_WINDOW: int = 60  # Time window in seconds
    RATE_LIMIT_USER_MAX: int = 100  # Max API calls per authenticated user per minute
    RATE_LIMIT_USER_WINDOW: int = 60  # Time window in seconds
    RATE_LIMIT_REGISTER_MAX: int = 5  # Max registration attempts per IP per hour
    RATE_LIMIT_REGISTER_WINDOW: int = 3600  # Registration window in seconds (1 hour)
    RATE_LIMIT_LOGIN_MAX: int = 10  # Max login attempts per IP per hour
    RATE_LIMIT_LOGIN_WINDOW: int = 3600  # Login window in seconds (1 hour)
    
    # Cache TTLs (in seconds)
    FLOW_CACHE_TTL: int = 3600  # 1 hour
    SESSION_CACHE_TTL: int = 1800  # 30 minutes
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    BCRYPT_ROUNDS: int = Field(12, ge=10, le=16)  # Password hashing rounds (10-16 recommended)
    
    # Database Connection Pool
    DB_POOL_SIZE: int = 10  # Number of permanent connections
    DB_MAX_OVERFLOW: int = 20  # Additional connections allowed beyond pool_size
    
    # HTTP Client Configuration
    HTTP_TIMEOUT: float = 30.0  # Timeout for external API calls in seconds
    HTTP_MAX_CONNECTIONS: int = 100  # Maximum concurrent HTTP connections
    HTTP_MAX_KEEPALIVE: int = 20  # Maximum keepalive connections
    
    # Redis Connection
    REDIS_SOCKET_TIMEOUT: int = 5  # Socket connection timeout in seconds
    REDIS_MAX_RECONNECT_ATTEMPTS: int = 3  # Maximum reconnection attempts
    REDIS_RECONNECT_BACKOFF_CAP: int = 30  # Maximum backoff time in seconds
    
    # Flow & Session Limits
    MAX_FLOW_SIZE: int = 1 * 1024 * 1024  # 1 MB - Maximum flow definition size
    API_TIMEOUT: int = 30  # API request timeout (deprecated, use HTTP_TIMEOUT)
    MAX_AUTO_PROGRESSION: int = 10  # Maximum consecutive nodes without user input
    SESSION_TIMEOUT_MINUTES: int = 30  # Session absolute timeout
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Application
    APP_NAME: str = "Bot Builder"
    APP_VERSION: str = "1.0.0"
    BASE_URL: str = "http://localhost:8000"  # Base URL for webhook URLs
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @model_validator(mode='after')
    def validate_secret_key(self):
        """Validate SECRET_KEY after all fields are loaded"""
        # Always require proper SECRET_KEY
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be set in environment and be at least 32 characters. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        # Additional production check
        if self.is_production:
            if self.SECRET_KEY in ["change-this-secret-key-in-production", "CHANGEME", "changeme"]:
                raise ValueError(
                    "SECRET_KEY cannot use placeholder value in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
        
        return self


# Create global settings instance
settings = Settings()