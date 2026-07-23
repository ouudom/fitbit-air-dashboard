from datetime import UTC, datetime
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from src.mcp_server import (
    _bearer_token,
    _principal,
    _registration_attempts,
    _require_query_scopes,
    app,
    disconnect_google_health,
    mcp,
)
from src.modules.agent_access.schemas import AgentScope
from src.modules.agent_access.service import AgentOAuthClientService, AgentPrincipal
from starlette.testclient import TestClient


def test_health_check_does_not_require_oauth() -> None:
    response = TestClient(app).get("/healthz", headers={"host": "localhost:8001"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mcp_endpoint_rejects_missing_oauth_access_token() -> None:
    response = TestClient(app).post("/mcp", headers={"host": "localhost:8001"}, json={})

    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["www-authenticate"]
    assert response.json() == {"detail": "Invalid or missing OAuth access token"}


def test_oauth_discovery_advertises_public_pkce_dcr_and_revocation() -> None:
    client = TestClient(app)
    authorization = client.get(
        "/.well-known/oauth-authorization-server",
        headers={"host": "localhost:8001"},
    )
    resource = client.get(
        "/.well-known/oauth-protected-resource/mcp",
        headers={"host": "localhost:8001"},
    )

    assert authorization.status_code == 200
    assert authorization.json()["grant_types_supported"] == [
        "authorization_code",
        "refresh_token",
    ]
    assert authorization.json()["code_challenge_methods_supported"] == ["S256"]
    assert authorization.json()["token_endpoint_auth_methods_supported"] == ["none"]
    assert authorization.json()["registration_endpoint"].endswith("/oauth/register")
    assert authorization.json()["revocation_endpoint"].endswith("/oauth/revoke")
    assert resource.status_code == 200
    assert resource.json()["resource"].endswith("/mcp")


def test_dynamic_registration_creates_public_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register = AsyncMock(
        return_value=SimpleNamespace(
            client_id="lso_public",
            client_name="Codex",
            redirect_uris=["http://127.0.0.1:1455/callback"],
            created_at=datetime(2026, 7, 23, tzinfo=UTC),
        )
    )
    monkeypatch.setattr(AgentOAuthClientService, "register_client", register)
    response = TestClient(app).post(
        "/oauth/register",
        headers={"host": "localhost:8001", "content-type": "application/json"},
        json={
            "client_name": "Codex",
            "redirect_uris": ["http://127.0.0.1:1455/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )

    assert response.status_code == 201
    assert response.json()["client_id"] == "lso_public"
    assert response.json()["token_endpoint_auth_method"] == "none"
    assert response.headers["cache-control"] == "no-store"
    register.assert_awaited_once_with(
        client_name="Codex",
        redirect_uris=["http://127.0.0.1:1455/callback"],
    )


def test_dynamic_registration_accepts_authorization_code_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register = AsyncMock(
        return_value=SimpleNamespace(
            client_id="lso_public",
            client_name="Hermes",
            redirect_uris=["http://localhost:1455/callback"],
            created_at=datetime(2026, 7, 23, tzinfo=UTC),
        )
    )
    monkeypatch.setattr(AgentOAuthClientService, "register_client", register, raising=False)
    response = TestClient(app).post(
        "/oauth/register",
        headers={"host": "localhost:8001"},
        json={
            "client_name": "Hermes",
            "redirect_uris": ["http://localhost:1455/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )

    assert response.status_code == 201
    assert response.json()["grant_types"] == ["authorization_code"]


def test_dynamic_registration_is_bounded() -> None:
    _registration_attempts.clear()
    _registration_attempts.extend([monotonic()] * 30)
    try:
        response = TestClient(app).post(
            "/oauth/register",
            headers={"host": "localhost:8001"},
            json={
                "client_name": "Codex",
                "redirect_uris": ["http://127.0.0.1:1455/callback"],
            },
        )
    finally:
        _registration_attempts.clear()

    assert response.status_code == 429
    assert response.json()["error"] == "temporarily_unavailable"


def test_registration_rejects_secret_clients_and_unsafe_redirects() -> None:
    client = TestClient(app)
    secret = client.post(
        "/oauth/register",
        headers={"host": "localhost:8001"},
        json={
            "client_name": "Claude",
            "redirect_uris": ["https://claude.ai/callback"],
            "token_endpoint_auth_method": "client_secret_post",
        },
    )
    unsafe = client.post(
        "/oauth/register",
        headers={"host": "localhost:8001"},
        json={
            "client_name": "Hermes",
            "redirect_uris": ["http://attacker.example/callback"],
        },
    )

    assert secret.status_code == 400
    assert secret.json()["error"] == "invalid_client_metadata"
    assert unsafe.status_code == 400
    assert unsafe.json()["error"] == "invalid_redirect_uri"


def test_authorize_requires_registered_exact_redirect_and_sends_browser_to_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookup = AsyncMock(
        return_value=SimpleNamespace(redirect_uris=["http://127.0.0.1:1455/callback"])
    )
    monkeypatch.setattr(AgentOAuthClientService, "get_client", lookup)
    params = {
        "response_type": "code",
        "client_id": "lso_public",
        "redirect_uri": "http://127.0.0.1:1455/callback",
        "state": "opaque-state",
        "scope": "today:read",
        "code_challenge": "A" * 43,
        "code_challenge_method": "S256",
        "resource": "http://localhost:8001/mcp",
    }

    response = TestClient(app).get(
        "/oauth/authorize",
        params=params,
        headers={"host": "localhost:8001"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("/oauth/consent?")
    lookup.assert_awaited_once_with("lso_public")


def test_authorize_rejects_unregistered_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookup = AsyncMock(
        return_value=SimpleNamespace(redirect_uris=["http://127.0.0.1:1455/callback"])
    )
    monkeypatch.setattr(AgentOAuthClientService, "get_client", lookup)
    response = TestClient(app).get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "lso_public",
            "redirect_uri": "http://127.0.0.1:1456/callback",
            "state": "opaque-state",
            "code_challenge": "A" * 43,
            "code_challenge_method": "S256",
        },
        headers={"host": "localhost:8001"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


def test_authorize_rejects_duplicate_scope_before_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect_uri = "http://127.0.0.1:1455/callback"
    lookup = AsyncMock(return_value=SimpleNamespace(redirect_uris=[redirect_uri]))
    monkeypatch.setattr(AgentOAuthClientService, "get_client", lookup, raising=False)
    response = TestClient(app).get(
        (
            "/oauth/authorize?response_type=code&client_id=lso_public"
            f"&redirect_uri={redirect_uri}"
            "&scope=ecg%3Aread&scope=today%3Aread"
            "&code_challenge=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            "&code_challenge_method=S256&resource=http%3A%2F%2Flocalhost%3A8001%2Fmcp"
            "&state=opaque"
        ),
        headers={"host": "localhost:8001"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith(f"{redirect_uri}?")
    assert "error=invalid_request" in response.headers["location"]
    assert "/oauth/consent" not in response.headers["location"]


def test_public_client_exchanges_code_with_pkce_and_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.modules.agent_access.service import IssuedOAuthAccessToken

    exchange = AsyncMock(
        return_value=IssuedOAuthAccessToken(
            access_token="lsoa_access",
            scopes=(AgentScope.TODAY_READ,),
            expires_in=3600,
            refresh_token="lsor_refresh",
        )
    )
    monkeypatch.setattr(AgentOAuthClientService, "exchange_authorization_code", exchange)
    response = TestClient(app).post(
        "/oauth/token",
        headers={"host": "localhost:8001"},
        data={
            "grant_type": "authorization_code",
            "client_id": "lso_public",
            "code": "one-time-code",
            "redirect_uri": "http://127.0.0.1:1455/callback",
            "code_verifier": "v" * 43,
            "resource": "http://localhost:8001/mcp",
        },
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] == "lsor_refresh"
    exchange.assert_awaited_once_with(
        client_id="lso_public",
        code="one-time-code",
        redirect_uri="http://127.0.0.1:1455/callback",
        code_verifier="v" * 43,
        resource="http://localhost:8001/mcp",
    )


def test_token_endpoint_rejects_client_secret_and_wrong_resource() -> None:
    client = TestClient(app)
    secret = client.post(
        "/oauth/token",
        headers={"host": "localhost:8001"},
        data={
            "grant_type": "refresh_token",
            "client_id": "lso_public",
            "client_secret": "forbidden",
            "refresh_token": "lsor_token",
        },
    )
    target = client.post(
        "/oauth/token",
        headers={"host": "localhost:8001"},
        data={
            "grant_type": "refresh_token",
            "client_id": "lso_public",
            "refresh_token": "lsor_token",
            "resource": "https://other.example/mcp",
        },
    )

    assert secret.status_code == 401
    assert secret.json()["error"] == "invalid_client"
    assert target.status_code == 400
    assert target.json()["error"] == "invalid_target"


def test_public_client_can_revoke_token(monkeypatch: pytest.MonkeyPatch) -> None:
    revoke = AsyncMock()
    monkeypatch.setattr(AgentOAuthClientService, "revoke_token", revoke)
    response = TestClient(app).post(
        "/oauth/revoke",
        headers={"host": "localhost:8001"},
        data={"client_id": "lso_public", "token": "lsor_token"},
    )

    assert response.status_code == 200
    revoke.assert_awaited_once_with("lsor_token", client_id="lso_public")


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
                "headers": [(b"authorization", b"Bearer lsoa_secret")],
            }
        )
        == "lsoa_secret"
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


def test_valid_oauth_access_token_initializes_stateless_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = AgentPrincipal(
        user_id=7,
        token_id=uuid4(),
        scopes=frozenset({AgentScope.PROFILE_READ}),
    )

    async def authenticate(
        _service: AgentOAuthClientService,
        raw_token: str,
        *,
        expected_resource: str,
    ) -> AgentPrincipal:
        assert raw_token == "lsoa_valid"
        assert expected_resource == "http://localhost:8001/mcp"
        return principal

    monkeypatch.setattr(AgentOAuthClientService, "authenticate_access_token", authenticate)
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={
                "host": "localhost:8001",
                "authorization": "Bearer lsoa_valid",
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
