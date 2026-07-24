from datetime import timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import Response
from pydantic import ValidationError
from src.core.config import Settings
from src.core.errors import AuthenticationError, NotFoundError
from src.core.time import utc_now
from src.modules.agent_access.models import McpToken
from src.modules.agent_access.router import create_mcp_token
from src.modules.agent_access.schemas import AgentScope, McpTokenCreate
from src.modules.agent_access.service import IssuedMcpToken, McpTokenService
from src.modules.auth.dependencies import Principal
from src.modules.auth.models import User


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_create_returns_secret_once_and_stores_only_digest() -> None:
    db = _db()
    issued = await McpTokenService(db).create(
        42,
        name="Codex",
        scopes=[AgentScope.TODAY_READ, AgentScope.SLEEP_READ],
        expires_at=utc_now() + timedelta(days=30),
    )

    assert issued.token.startswith("lsmcp_")
    assert issued.record.user_id == 42
    assert issued.record.token_hash == sha256(issued.token.encode()).hexdigest()
    assert issued.record.token_hash != issued.token
    assert issued.record.token_prefix == issued.token[:16]
    assert issued.record.scopes == ["today:read", "sleep:read"]
    db.add.assert_called_once_with(issued.record)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(issued.record)


@pytest.mark.asyncio
async def test_authenticate_resolves_token_owned_user_and_records_use() -> None:
    db = _db()
    token_id = uuid4()
    row = McpToken(
        id=token_id,
        user_id=42,
        name="Codex",
        token_prefix="lsmcp_example",
        token_hash="stored",
        scopes=["today:read", "sync:read"],
    )
    db.scalar.return_value = row
    db.get.return_value = User(
        id=42,
        name="Owner",
        email="owner@example.com",
        password_hash="unused",
    )

    principal = await McpTokenService(db).authenticate("lsmcp_a-valid-looking-secret")

    assert principal.user_id == 42
    assert principal.token_id == token_id
    assert principal.scopes == frozenset({AgentScope.TODAY_READ, AgentScope.SYNC_READ})
    assert principal.has_scope(AgentScope.TODAY_READ)
    assert row.last_used_at is not None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_or_expired_token() -> None:
    db = _db()
    db.scalar.return_value = None

    with pytest.raises(AuthenticationError, match="Invalid MCP token"):
        await McpTokenService(db).authenticate("lsmcp_unknown")

    expired = McpToken(
        id=uuid4(),
        user_id=42,
        name="Old",
        token_prefix="lsmcp_expired",
        token_hash="stored",
        scopes=["today:read"],
        expires_at=utc_now() - timedelta(seconds=1),
    )
    db.scalar.return_value = expired
    with pytest.raises(AuthenticationError, match="Invalid MCP token"):
        await McpTokenService(db).authenticate("lsmcp_expired-secret")

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_is_scoped_to_browser_user() -> None:
    db = _db()
    db.scalar.return_value = None

    with pytest.raises(NotFoundError, match="MCP token not found"):
        await McpTokenService(db).revoke(user_id=42, token_id=uuid4())

    db.commit.assert_not_awaited()


def test_token_request_requires_explicit_valid_scopes_and_aware_expiry() -> None:
    with pytest.raises(ValidationError):
        McpTokenCreate(name="Codex", scopes=[])
    with pytest.raises(ValidationError):
        McpTokenCreate(
            name="Codex",
            scopes=[AgentScope.TODAY_READ],
            expires_at=(utc_now() + timedelta(days=1)).replace(tzinfo=None),
        )

    payload = McpTokenCreate(
        name=" Codex ",
        scopes=[AgentScope.TODAY_READ, AgentScope.TODAY_READ],
    )
    assert payload.name == "Codex"
    assert payload.scopes == [AgentScope.TODAY_READ]


@pytest.mark.asyncio
async def test_issued_token_response_is_not_cacheable() -> None:
    issued = IssuedMcpToken(
        token="lsmcp_secret",
        record=McpToken(
            id=uuid4(),
            user_id=42,
            name="Codex",
            token_prefix="lsmcp_secret",
            token_hash="digest",
            scopes=["today:read"],
            created_at=utc_now(),
        ),
    )
    response = Response()
    principal = Principal(user_id=42, email="owner@example.com", session_id=uuid4())
    with patch.object(McpTokenService, "create", AsyncMock(return_value=issued)):
        result = await create_mcp_token(
            McpTokenCreate(name="Codex", scopes=[AgentScope.TODAY_READ]),
            response,
            principal,
            _db(),
            Settings(mcp_public_url="https://lifestats.example.com/mcp"),
        )

    assert response.headers["cache-control"] == "no-store"
    assert result.token == "lsmcp_secret"
    assert result.mcp_url == "https://lifestats.example.com/mcp?token=lsmcp_secret"
