from fastapi.testclient import TestClient
from src.core.config import Settings, get_settings
from src.main import create_app


def test_local_environment_disables_agent_access() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="local",
        _env_file=None,
    )

    with TestClient(app) as client:
        capabilities = client.get("/api/v1/capabilities")
        tokens = client.get("/api/v1/mcp-tokens")

    assert capabilities.status_code == 200
    assert capabilities.json() == {"agentAccessEnabled": False}
    assert tokens.status_code == 404


def test_non_local_environment_enables_agent_access() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        _env_file=None,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json() == {"agentAccessEnabled": True}
