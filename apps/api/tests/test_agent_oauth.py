from datetime import timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.core.config import Settings
from src.core.errors import AuthenticationError
from src.core.time import utc_now
from src.modules.agent_access.models import (
    AgentOAuthClient,
    AgentOAuthCredential,
    AgentOAuthGrant,
    OAuthCredentialKind,
)
from src.modules.agent_access.router import decide_authorization, preview_authorization
from src.modules.agent_access.schemas import AgentScope, OAuthAuthorizationDecisionRequest
from src.modules.agent_access.service import (
    AgentOAuthClientService,
    InvalidOAuthGrantError,
    _pkce_challenge,
)
from src.modules.auth.dependencies import Principal
from src.modules.auth.models import User
from starlette.requests import Request


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = Mock()
    return db


def _client() -> AgentOAuthClient:
    return AgentOAuthClient(
        id=uuid4(),
        client_id="lso_client",
        client_name="Codex",
        redirect_uris=["http://127.0.0.1:8765/callback"],
    )


def _grant(client: AgentOAuthClient) -> AgentOAuthGrant:
    return AgentOAuthGrant(
        id=uuid4(),
        oauth_client_id=client.id,
        user_id=42,
        scopes=["today:read"],
        resource="https://stats.example/mcp",
    )


@pytest.mark.asyncio
async def test_registers_public_client_without_user_or_secret() -> None:
    db = _db()

    row = await AgentOAuthClientService(db).register_client(
        client_name=" Codex ",
        redirect_uris=[
            "http://127.0.0.1:8765/callback",
            "http://127.0.0.1:8765/callback",
        ],
    )

    assert row.client_id.startswith("lso_")
    assert row.client_name == "Codex"
    assert row.redirect_uris == ["http://127.0.0.1:8765/callback"]
    assert not hasattr(row, "client_secret_hash")
    assert not hasattr(row, "user_id")
    db.add.assert_called_once_with(row)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_authorization_code_requires_registered_redirect_and_s256() -> None:
    db = _db()
    client = _client()
    grant = _grant(client)
    service = AgentOAuthClientService(db)
    with (
        patch.object(service, "get_client", AsyncMock(return_value=client)),
        patch.object(service, "create_or_update_grant", AsyncMock(return_value=grant)),
    ):
        with pytest.raises(InvalidOAuthGrantError, match="Redirect URI"):
            await service.issue_authorization_code(
                user_id=42,
                client_id=client.client_id,
                redirect_uri="http://evil.example/callback",
                code_challenge=_pkce_challenge("v" * 64),
                requested_scopes=["today:read"],
                resource=grant.resource,
            )
        with pytest.raises(InvalidOAuthGrantError, match="S256"):
            await service.issue_authorization_code(
                user_id=42,
                client_id=client.client_id,
                redirect_uri=client.redirect_uris[0],
                code_challenge="plain-verifier",
                requested_scopes=["today:read"],
                resource=grant.resource,
            )


@pytest.mark.asyncio
async def test_scope_change_revokes_existing_grant_credentials() -> None:
    db = _db()
    client = _client()
    grant = _grant(client)
    db.scalar.side_effect = [client, client, grant]
    db.get.return_value = User(
        id=42,
        name="Owner",
        email="owner@example.com",
        password_hash="unused",
    )

    updated = await AgentOAuthClientService(db).create_or_update_grant(
        42,
        client_id=client.client_id,
        scopes=["sleep:read"],
        resource=grant.resource,
    )

    assert updated.scopes == ["sleep:read"]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_code_exchange_consumes_unified_credential_and_issues_token_pair() -> None:
    db = _db()
    client = _client()
    grant = _grant(client)
    verifier = "v" * 64
    code = AgentOAuthCredential(
        id=uuid4(),
        grant_id=grant.id,
        kind=OAuthCredentialKind.AUTHORIZATION_CODE.value,
        value_hash=sha256(b"code").hexdigest(),
        scopes=["today:read"],
        redirect_uri=client.redirect_uris[0],
        code_challenge=_pkce_challenge(verifier),
        expires_at=utc_now() + timedelta(minutes=5),
    )
    result = Mock()
    result.one_or_none.return_value = (code, grant)
    db.execute.return_value = result
    service = AgentOAuthClientService(db)
    with patch.object(service, "get_client", AsyncMock(return_value=client)):
        issued = await service.exchange_authorization_code(
            client_id=client.client_id,
            code="code",
            redirect_uri=client.redirect_uris[0],
            code_verifier=verifier,
            resource=grant.resource,
        )

    assert code.consumed_at is not None
    assert issued.access_token.startswith("lsoa_")
    assert issued.refresh_token is not None
    assert issued.refresh_token.startswith("lsor_")
    credentials = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], AgentOAuthCredential)
    ]
    assert {row.kind for row in credentials} == {"access_token", "refresh_token"}
    assert all(
        row.value_hash not in {issued.access_token, issued.refresh_token} for row in credentials
    )


@pytest.mark.asyncio
async def test_access_token_resolves_user_grant_and_checks_resource() -> None:
    db = _db()
    client = _client()
    grant = _grant(client)
    access = AgentOAuthCredential(
        id=uuid4(),
        grant_id=grant.id,
        kind=OAuthCredentialKind.ACCESS_TOKEN.value,
        value_hash=sha256(b"lsoa_secret").hexdigest(),
        scopes=["today:read"],
        expires_at=utc_now() + timedelta(hours=1),
    )
    result = Mock()
    result.one_or_none.return_value = (access, grant, client)
    db.execute.return_value = result
    db.get.return_value = User(
        id=42,
        name="Owner",
        email="owner@example.com",
        password_hash="unused",
    )

    principal = await AgentOAuthClientService(db).authenticate_access_token(
        "lsoa_secret",
        expected_resource=grant.resource,
    )

    assert principal.user_id == 42
    assert principal.scopes == frozenset({AgentScope.TODAY_READ})
    assert access.last_used_at is not None

    with pytest.raises(AuthenticationError, match="audience"):
        await AgentOAuthClientService(db).authenticate_access_token(
            "lsoa_secret",
            expected_resource="https://other.example/mcp",
        )


@pytest.mark.asyncio
async def test_reused_refresh_token_revokes_active_grant_credentials() -> None:
    db = _db()
    client = _client()
    grant = _grant(client)
    reused = AgentOAuthCredential(
        id=uuid4(),
        grant_id=grant.id,
        kind=OAuthCredentialKind.REFRESH_TOKEN.value,
        value_hash=sha256(b"lsor_old").hexdigest(),
        scopes=["today:read"],
        expires_at=utc_now() + timedelta(days=1),
        consumed_at=utc_now(),
    )
    missing = Mock()
    missing.one_or_none.return_value = None
    found = Mock()
    found.scalar_one_or_none.return_value = reused
    updated = Mock()
    db.execute.side_effect = [missing, found, updated]
    service = AgentOAuthClientService(db)
    with patch.object(service, "get_client", AsyncMock(return_value=client)):
        with pytest.raises(InvalidOAuthGrantError):
            await service.refresh_access_token(
                client_id=client.client_id,
                refresh_token="lsor_old",
                requested_scopes=[],
                resource=grant.resource,
            )

    assert db.execute.await_count == 3
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_preview_validates_client_and_shows_requested_scopes() -> None:
    db = _db()
    client = _client()
    settings = Settings(
        mcp_public_url="https://stats.example/mcp",
        mcp_oauth_issuer_url="https://stats.example",
    )
    with patch.object(
        AgentOAuthClientService,
        "get_client",
        AsyncMock(return_value=client),
    ):
        preview = await preview_authorization(
            Request({"type": "http", "query_string": b"", "headers": []}),
            Principal(user_id=42, email="owner@example.com", session_id=uuid4()),
            client_id=client.client_id,
            redirect_uri=client.redirect_uris[0],
            response_type="code",
            code_challenge="A" * 43,
            code_challenge_method="S256",
            resource=settings.mcp_public_url,
            scope="today:read sleep:read",
            state="opaque",
            db=db,
            settings=settings,
        )

    assert preview.client_name == "Codex"
    assert preview.redirect_uri == client.redirect_uris[0]
    assert preview.scopes == [AgentScope.TODAY_READ, AgentScope.SLEEP_READ]


@pytest.mark.asyncio
async def test_browser_preview_rejects_duplicate_security_parameters() -> None:
    settings = Settings(
        mcp_public_url="https://stats.example/mcp",
        mcp_oauth_issuer_url="https://stats.example",
    )
    with pytest.raises(HTTPException, match="Duplicate OAuth parameter"):
        await preview_authorization(
            Request(
                {
                    "type": "http",
                    "query_string": b"scope=ecg%3Aread&scope=today%3Aread",
                    "headers": [],
                }
            ),
            Principal(user_id=42, email="owner@example.com", session_id=uuid4()),
            client_id="lso_client",
            redirect_uri="http://127.0.0.1:8765/callback",
            response_type="code",
            code_challenge="A" * 43,
            code_challenge_method="S256",
            resource=settings.mcp_public_url,
            scope="today:read",
            db=_db(),
            settings=settings,
        )


@pytest.mark.asyncio
async def test_browser_approval_issues_user_bound_code_and_preserves_state() -> None:
    db = _db()
    client = _client()
    settings = Settings(
        mcp_public_url="https://stats.example/mcp",
        mcp_oauth_issuer_url="https://stats.example",
    )
    principal = Principal(user_id=42, email="owner@example.com", session_id=uuid4())
    payload = OAuthAuthorizationDecisionRequest(
        approved=True,
        client_id=client.client_id,
        redirect_uri=client.redirect_uris[0],
        response_type="code",
        code_challenge="A" * 43,
        code_challenge_method="S256",
        scope="today:read",
        resource=settings.mcp_public_url,
        state="opaque state",
    )
    issue = AsyncMock(return_value="one-time-code")
    with (
        patch.object(
            AgentOAuthClientService,
            "get_client",
            AsyncMock(return_value=client),
        ),
        patch.object(AgentOAuthClientService, "issue_authorization_code", issue),
    ):
        response = await decide_authorization(
            payload,
            principal,
            db=db,
            settings=settings,
        )

    assert "code=one-time-code" in response.redirect_to
    assert "state=opaque+state" in response.redirect_to
    assert "iss=https%3A%2F%2Fstats.example" in response.redirect_to
    issue.assert_awaited_once_with(
        user_id=42,
        client_id=client.client_id,
        redirect_uri=client.redirect_uris[0],
        code_challenge="A" * 43,
        requested_scopes=["today:read"],
        resource=settings.mcp_public_url,
    )
