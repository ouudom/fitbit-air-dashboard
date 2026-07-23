import pytest
from pydantic import ValidationError
from src.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "database_url": "postgresql+asyncpg://lifestats:secret@db:5432/lifestats",
        "redis_url": "redis://redis:6379/0",
        "setup_token": "s" * 32,
        "token_encryption_key": "t" * 32,
        "google_client_id": "client-id",
        "google_client_secret": "client-secret",
        "redirect_uri": "https://health.example/api/v1/oauth/google-health/callback",
        "mcp_public_url": "https://health.example/mcp",
        "mcp_oauth_issuer_url": "https://health.example",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_production_requires_real_secrets_and_https_callback() -> None:
    with pytest.raises(ValidationError, match="Missing production settings"):
        Settings(app_env="production", _env_file=None)
    with pytest.raises(ValidationError, match="REDIRECT_URI must use HTTPS"):
        production_settings(redirect_uri="http://health.example/callback")
    with pytest.raises(ValidationError, match="MCP_PUBLIC_URL must use HTTPS"):
        production_settings(mcp_public_url="http://health.example/mcp")


def test_valid_production_polling_configuration() -> None:
    settings = production_settings()
    assert settings.secure_cookies is True
    assert settings.google_health_webhook_enabled is False


def test_enabled_webhook_requires_complete_https_configuration() -> None:
    with pytest.raises(ValidationError, match="Missing webhook settings"):
        production_settings(google_health_webhook_enabled=True)
    with pytest.raises(ValidationError, match="GOOGLE_HEALTH_WEBHOOK_URL must use HTTPS"):
        production_settings(
            google_health_webhook_enabled=True,
            google_cloud_project_number="123",
            google_health_subscriber_id="subscriber",
            google_health_webhook_url="http://health.example/webhook",
            google_health_webhook_auth_secret="webhook-secret",
        )
