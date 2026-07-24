from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "local"
    app_timezone: str = "Asia/Phnom_Penh"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://lifestats:change-me@localhost:5432/lifestats"
    redis_url: str = "redis://localhost:6379/0"
    setup_token: str = ""
    session_lifetime_hours: int = 24 * 7
    token_encryption_key: str = ""
    app_key: str = ""
    mcp_public_url: str = "http://localhost:8001/mcp"
    google_client_id: str = ""
    google_client_secret: str = ""
    redirect_uri: str = "http://localhost:3000/api/v1/oauth/google-health/callback"
    scopes: str = Field(
        default=(
            "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly "
            "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly "
            "https://www.googleapis.com/auth/googlehealth.nutrition.readonly "
            "https://www.googleapis.com/auth/googlehealth.sleep.readonly "
            "https://www.googleapis.com/auth/googlehealth.ecg.readonly "
            "https://www.googleapis.com/auth/googlehealth.irn.readonly "
            "https://www.googleapis.com/auth/googlehealth.location.readonly"
        )
    )
    google_health_url: str = "https://health.googleapis.com/v4"
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_revoke_url: str = "https://oauth2.googleapis.com/revoke"
    google_cloud_project_number: str = ""
    google_health_subscriber_id: str = ""
    google_health_webhook_url: str = ""
    google_health_webhook_auth_secret: str = ""
    google_health_webhook_enabled: bool = False
    google_health_webhook_keyset_url: str = (
        "https://www.gstatic.com/googlehealthapi/webhooks/webhooks_public_keyset.json"
    )
    google_health_webhook_keyset_ttl_seconds: int = 3600

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @field_validator("mcp_public_url")
    @classmethod
    def validate_mcp_public_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            not parsed.scheme
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("MCP_PUBLIC_URL must be an absolute URL without query or fragment")
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env != "production":
            return self

        required = {
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "SETUP_TOKEN": self.setup_token,
            "TOKEN_ENCRYPTION_KEY": self.token_encryption_key,
            "GOOGLE_CLIENT_ID": self.google_client_id,
            "GOOGLE_CLIENT_SECRET": self.google_client_secret,
            "REDIRECT_URI": self.redirect_uri,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing production settings: {', '.join(missing)}")
        if "change-me" in self.database_url:
            raise ValueError("DATABASE_URL still contains placeholder credentials")
        if len(self.setup_token) < 32:
            raise ValueError("SETUP_TOKEN must contain at least 32 characters in production")
        if len(self.token_encryption_key) < 32:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY must contain at least 32 characters in production"
            )
        if not self.redirect_uri.startswith("https://"):
            raise ValueError("REDIRECT_URI must use HTTPS in production")
        if not self.mcp_public_url.startswith("https://"):
            raise ValueError("MCP_PUBLIC_URL must use HTTPS in production")
        if self.google_health_webhook_enabled:
            webhook_required = {
                "GOOGLE_CLOUD_PROJECT_NUMBER": self.google_cloud_project_number,
                "GOOGLE_HEALTH_SUBSCRIBER_ID": self.google_health_subscriber_id,
                "GOOGLE_HEALTH_WEBHOOK_URL": self.google_health_webhook_url,
                "GOOGLE_HEALTH_WEBHOOK_AUTH_SECRET": self.google_health_webhook_auth_secret,
            }
            webhook_missing = [name for name, value in webhook_required.items() if not value]
            if webhook_missing:
                raise ValueError(f"Missing webhook settings: {', '.join(webhook_missing)}")
            if not self.google_health_webhook_url.startswith("https://"):
                raise ValueError("GOOGLE_HEALTH_WEBHOOK_URL must use HTTPS in production")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.app_env not in {"local", "test"}

    @property
    def agent_access_enabled(self) -> bool:
        return self.app_env != "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
