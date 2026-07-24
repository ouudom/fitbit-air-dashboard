from uuid import uuid4

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from src.mcp_server import (
    _principal,
    _query_token,
    _require_query_scopes,
    app,
    disconnect_google_health,
    mcp,
)
from src.modules.agent_access.schemas import AgentScope
from src.modules.agent_access.service import AgentPrincipal, McpTokenService
from starlette.testclient import TestClient


def test_health_check_does_not_require_mcp_token() -> None:
    response = TestClient(app).get("/healthz", headers={"host": "localhost:8001"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mcp_endpoint_rejects_missing_mcp_token() -> None:
    response = TestClient(app).post("/mcp", headers={"host": "localhost:8001"}, json={})

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Invalid or missing MCP token"}


def test_query_parser_requires_one_unambiguous_token() -> None:
    assert _query_token({"type": "http", "headers": [], "query_string": b""}) is None
    assert (
        _query_token(
            {
                "type": "http",
                "headers": [],
                "query_string": b"token=lsmcp_secret",
            }
        )
        == "lsmcp_secret"
    )
    assert (
        _query_token(
            {
                "type": "http",
                "headers": [],
                "query_string": b"token=first&token=second",
            }
        )
        is None
    )
    assert (
        _query_token(
            {
                "type": "http",
                "headers": [(b"authorization", b"Bearer ignored")],
                "query_string": b"token=lsmcp_secret",
            }
        )
        is None
    )
    assert (
        _query_token(
            {
                "type": "http",
                "headers": [],
                "query_string": b"token=lsmcp_secret&extra=value",
            }
        )
        is None
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


def test_valid_mcp_token_initializes_stateless_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = AgentPrincipal(
        user_id=7,
        token_id=uuid4(),
        scopes=frozenset({AgentScope.PROFILE_READ}),
    )

    async def authenticate(_service: McpTokenService, raw_token: str) -> AgentPrincipal:
        assert raw_token == "lsmcp_valid"
        return principal

    monkeypatch.setattr(McpTokenService, "authenticate", authenticate)
    with TestClient(app) as client:
        response = client.post(
            "/mcp?token=lsmcp_valid",
            headers={
                "host": "localhost:8001",
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
