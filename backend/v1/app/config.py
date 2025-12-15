"""
Configuration Management
Loads settings from environment variables using Pydantic with nested structure
Improved validation and organization
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, Field, field_validator
from typing import List


class DatabaseConfig(BaseSettings):
    """Database configuration group"""
    url: str = "postgresql+asyncpg://botbuilder:password@localhost:5432/botbuilder"
    pool_size: int = Field(10, ge=1, le=100, description="Number of permanent connections")
    max_overflow: int = Field(20, ge=0, le=100, description="Additional connections beyond pool_size")
    echo: bool = Field(False, description="Log all SQL statements")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith('postgresql'):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql:// or postgresql+asyncpg://)")
        return v


class RedisConfig(BaseSettings):
    """Redis configuration group"""
    url: str = "redis://localhost:6379/0"
    enabled: bool = True
    socket_timeout: int = Field(5, ge=1, le=30, description="Socket connection timeout in seconds")
    socket_connect_timeout: int = Field(2, ge=1, le=10, description="Initial connection timeout")
    max_reconnect_attempts: int = Field(3, ge=0, le=10, description="Maximum reconnection attempts")
    reconnect_backoff_cap: int = Field(30, ge=1, le=300, description="Maximum backoff time in seconds")


class CacheConfig(BaseSettings):
    """Cache TTL configuration"""
    flow_ttl: int = Field(3600, ge=60, description="Flow cache TTL in seconds (1 hour)")
    session_ttl: int = Field(1800, ge=60, description="Session cache TTL in seconds (30 minutes)")


class SecurityConfig(BaseSettings):
    """Security and authentication configuration"""
    secret_key: str = Field(..., min_length=32, description="JWT secret key (min 32 chars)")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(120, ge=1, le=43200, description="JWT token expiration (max 30 days)")
    bcrypt_rounds: int = Field(12, ge=10, le=16, description="Password hashing rounds (10-16 recommended)")

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in ["change-this-secret-key-in-production", "CHANGEME", "changeme", "secret"]:
            raise ValueError(
                "SECRET_KEY cannot use placeholder value. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v


class HTTPClientConfig(BaseSettings):
    """HTTP client configuration for external API calls"""
    timeout: float = Field(30.0, ge=1.0, le=300.0, description="Request timeout in seconds")
    max_connections: int = Field(100, ge=10, le=1000, description="Maximum concurrent connections")
    max_keepalive: int = Field(20, ge=5, le=100, description="Maximum keepalive connections")


class FlowConstraintsConfig(BaseSettings):
    """Flow execution constraints and limits"""
    max_flow_size: int = Field(1048576, ge=1024, description="Maximum flow definition size in bytes (1 MB)")
    max_auto_progression: int = Field(10, ge=1, le=50, description="Maximum consecutive nodes without user input")
    session_timeout_minutes: int = Field(30, ge=1, le=1440, description="Session absolute timeout (max 24 hours)")


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration"""
    webhook_max: int = Field(10, ge=1, description="Max webhook requests per channel user per window")
    webhook_window: int = Field(60, ge=1, description="Webhook rate limit window in seconds")
    user_max: int = Field(100, ge=1, description="Max API calls per authenticated user per window")
    user_window: int = Field(60, ge=1, description="User rate limit window in seconds")
    register_max: int = Field(5, ge=1, description="Max registration attempts per IP per window")
    register_window: int = Field(3600, ge=60, description="Registration window in seconds (1 hour)")
    login_max: int = Field(10, ge=1, description="Max login attempts per IP per window")
    login_window: int = Field(3600, ge=60, description="Login window in seconds (1 hour)")


class Settings(BaseSettings):
    """
    Main application settings with nested configuration groups

    Environment variables support nested access using double underscore:
    - DATABASE__URL=postgresql://...
    - REDIS__ENABLED=true
    - SECURITY__SECRET_KEY=...
    """

    # Application metadata
    app_name: str = "Bot Builder"
    app_version: str = "1.0.0"
    environment: str = Field("development", pattern="^(development|staging|production)$")
    debug: bool = True
    base_url: str = "http://localhost:8000"

    # CORS configuration
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Nested configuration groups
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    http_client: HTTPClientConfig = Field(default_factory=HTTPClientConfig)
    flow_constraints: FlowConstraintsConfig = Field(default_factory=FlowConstraintsConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore"  # Ignore extra env vars
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"

    @model_validator(mode='after')
    def validate_cross_field(self):
        """Cross-field validation"""
        # Redis URL required when enabled
        if self.redis.enabled and not self.redis.url:
            raise ValueError("REDIS__URL is required when REDIS__ENABLED=true")

        # Production-specific validations
        if self.is_production:
            if self.debug:
                raise ValueError("DEBUG must be False in production")

            if self.security.access_token_expire_minutes > 1440:  # 24 hours
                raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES should not exceed 24 hours in production")

        return self


# Create global settings instance
settings = Settings()
