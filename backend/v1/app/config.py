"""
Configuration Management
Loads settings from environment variables using Pydantic with nested structure
Improved validation and organization
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, Field, field_validator, HttpUrl
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
    encryption_key: str = Field(..., min_length=44, description="Fernet encryption key for PII (44 chars base64)")
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

    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """
        Validate Fernet encryption key format

        Fernet keys must be 32 URL-safe base64-encoded bytes (44 characters).
        Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
        """
        from cryptography.fernet import Fernet

        if v in ["change-this-encryption-key-in-production", "CHANGEME", "changeme"]:
            raise ValueError(
                "ENCRYPTION_KEY cannot use placeholder value. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        # Validate format by attempting to create Fernet cipher
        try:
            Fernet(v.encode('utf-8'))
        except Exception as e:
            raise ValueError(
                f"ENCRYPTION_KEY is not a valid Fernet key: {e}. "
                f"Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        return v


class GoogleOAuthConfig(BaseSettings):
    """Google OAuth2 configuration"""
    client_id: str = Field("", description="Google OAuth2 Client ID")
    client_secret: str = Field("", description="Google OAuth2 Client Secret")
    redirect_uri: str = Field("http://localhost:8000/auth/google/callback", description="OAuth2 redirect URI")

    model_config = SettingsConfigDict(env_prefix="GOOGLE_")


class HTTPClientConfig(BaseSettings):
    """HTTP client configuration for external API calls"""
    timeout: float = Field(30.0, description="Request timeout in seconds (FIXED at 30s per specification)")
    max_connections: int = Field(100, ge=10, le=1000, description="Maximum concurrent connections")
    max_keepalive: int = Field(20, ge=5, le=100, description="Maximum keepalive connections")

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Enforce fixed 30-second timeout as per BOT_BUILDER_SPECIFICATIONS.md"""
        if v != 30.0:
            raise ValueError(
                "API request timeout must be exactly 30 seconds (not configurable per specification). "
                "See BOT_BUILDER_SPECIFICATIONS.md line 1619-1621, 1943-1944."
            )
        return v


class FlowConstraintsConfig(BaseSettings):
    """Flow execution constraints and limits"""
    max_flow_size: int = Field(1048576, ge=1024, description="Maximum flow definition size in bytes (1 MB)")
    max_auto_progression: int = Field(10, ge=1, le=50, description="Maximum consecutive nodes without user input")
    session_timeout_minutes: int = Field(30, description="Session absolute timeout (FIXED at 30 minutes per specification)")

    @field_validator('session_timeout_minutes')
    @classmethod
    def validate_session_timeout(cls, v: int) -> int:
        """Enforce fixed 30-minute session timeout as per BOT_BUILDER_SPECIFICATIONS.md"""
        if v != 30:
            raise ValueError(
                "Session timeout must be exactly 30 minutes (not configurable per specification). "
                "See BOT_BUILDER_SPECIFICATIONS.md line 1618, 2803-2807."
            )
        return v


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


class EvolutionAPIConfig(BaseSettings):
    """Evolution API configuration (shared/managed instance)"""
    url: str = Field(
        default="http://localhost:8080",
        description="Evolution API base URL (managed by platform)"
    )
    api_key: str = Field(
        default="",
        min_length=0,
        description="Evolution API authentication key"
    )
    enabled: bool = Field(
        default=False,
        description="Enable WhatsApp integration via Evolution API"
    )
    webhook_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for webhooks (e.g., https://yourplatform.com)"
    )

    model_config = SettingsConfigDict(env_prefix="EVOLUTION_API__")


class ObservabilityConfig(BaseSettings):
    """Observability configuration (Sentry, Prometheus)"""
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking (leave empty to disable)"
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sentry performance tracing sample rate (0.0-1.0)"
    )
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint at /metrics"
    )

    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY__")


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
    frontend_url: str = "http://localhost:3000"

    # CORS configuration
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Nested configuration groups
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    google: GoogleOAuthConfig = Field(default_factory=GoogleOAuthConfig)
    http_client: HTTPClientConfig = Field(default_factory=HTTPClientConfig)
    flow_constraints: FlowConstraintsConfig = Field(default_factory=FlowConstraintsConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    evolution_api: EvolutionAPIConfig = Field(default_factory=EvolutionAPIConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

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

            if self.security.access_token_expire_minutes > 4320:  # 3 days
                raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES should not exceed 3 days in production")

        return self


# Create global settings instance
settings = Settings()
