from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "local"
    app_timezone: str = "Asia/Phnom_Penh"
    database_url: str = "postgresql+asyncpg://fitbit:change-me@localhost:5432/fitbit_air"
    redis_url: str = "redis://localhost:6379/0"
    setup_token: str = ""
    session_lifetime_hours: int = 24 * 7
    token_encryption_key: str = ""
    app_key: str = ""
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

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def secure_cookies(self) -> bool:
        return self.app_env not in {"local", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
