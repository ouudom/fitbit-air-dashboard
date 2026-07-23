from uuid import uuid4

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from src.mcp_server import (
    _bearer_token,
    _principal,
    _require_query_scopes,
    app,
    disconnect_google_health,
    mcp,
)
from src.modules.agent_access.schemas import AgentScope
from src.modules.agent_access.service import AgentPrincipal, AgentTokenService
from starlette.testclient import TestClient


def test_health_check_does_not_require_agent_token() -> None:
    response = TestClient(app).get("/healthz", headers={"host": "localhost:8001"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mcp_endpoint_rejects_missing_agent_token() -> None:
    response = TestClient(app).post("/mcp", headers={"host": "localhost:8001"}, json={})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing agent token"}


def test_bearer_parser_rejects_ambiguous_or_malformed_headers() -> None:
    assert _bearer_token({"type": "http", "headers": []}) is None
    assert (
        _bearer_token(
            {
                "type": "http",
                "headers": [(b"authorization", b"Basic abc")],
            }
        )
        is None
    )
    assert (
        _bearer_token(
            {
                "type": "http",
                "headers": [
                    (b"authorization", b"Bearer first"),
                    (b"authorization", b"Bearer second"),
                ],
            }
        )
        is None
    )
    assert (
        _bearer_token(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer lstm_secret")],
            }
        )
        == "lstm_secret"
    )


def test_complete_supported_tool_surface_is_registered() -> None:
    assert {tool.name for tool in mcp._tool_manager.list_tools()} == {
        "disconnect_google_health",
        "get_activity_trend",
        "get_body_measurements",
        "get_connection_status",
        "get_data_freshness",
        "get_data_type_sync_status",
        "get_electrocardiogram",
        "get_exercise",
        "get_exercise_export",
        "get_fitness_summary",
        "get_google_health_status",
        "get_health_summary",
        "get_heart_rate_zones",
        "get_measurement_latest",
        "get_measurement_trend",
        "get_nutrition_summary",
        "get_profile",
        "get_sleep_session",
        "get_sleep_summary",
        "get_sleep_trend",
        "get_sync_status",
        "get_timeline",
        "get_today",
        "list_capabilities",
        "list_electrocardiograms",
        "list_exercises",
        "list_hydration_logs",
        "list_irregular_rhythm_notifications",
        "list_nutrition_logs",
        "list_sleep_sessions",
        "query_health_data",
        "start_google_health_connection",
        "trigger_sync",
    }


def test_generic_query_requires_sensitive_scope_separately() -> None:
    principal = AgentPrincipal(
        user_id=7,
        token_id=uuid4(),
        scopes=frozenset({AgentScope.HEALTH_READ}),
    )
    context_token = _principal.set(principal)
    try:
        _require_query_scopes(principal, ["weight"])
        try:
            _require_query_scopes(principal, ["electrocardiogram"])
        except Exception as exc:
            assert "ecg:read" in str(exc)
        else:
            raise AssertionError("ECG query accepted without ecg:read")
    finally:
        _principal.reset(context_token)


@pytest.mark.asyncio
async def test_disconnect_requires_explicit_confirmation() -> None:
    with pytest.raises(ToolError, match="confirm=true"):
        await disconnect_google_health()


def test_valid_agent_token_initializes_stateless_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = AgentPrincipal(
        user_id=7,
        token_id=uuid4(),
        scopes=frozenset({AgentScope.PROFILE_READ}),
    )

    async def authenticate(_service: AgentTokenService, raw_token: str) -> AgentPrincipal:
        assert raw_token == "lstm_valid"
        return principal

    monkeypatch.setattr(AgentTokenService, "authenticate", authenticate)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "host": "localhost:8001",
                "authorization": "Bearer lstm_valid",
                "accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "LifeStats"
