from datetime import timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import Response
from pydantic import ValidationError
from src.core.errors import AuthenticationError, NotFoundError
from src.core.time import utc_now
from src.modules.agent_access.models import AgentToken
from src.modules.agent_access.router import create_agent_token
from src.modules.agent_access.schemas import AgentScope, AgentTokenCreate
from src.modules.agent_access.service import AgentTokenService, IssuedAgentToken
from src.modules.auth.dependencies import Principal
from src.modules.auth.models import User


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = Mock()
    return db


@pytest.mark.asyncio
async def test_create_returns_secret_once_and_stores_only_digest() -> None:
    db = _db()
    issued = await AgentTokenService(db).create(
        42,
        name="Hermes",
        scopes=[AgentScope.TODAY_READ, AgentScope.SLEEP_READ],
        expires_at=utc_now() + timedelta(days=30),
    )

    assert issued.token.startswith("lstm_")
    assert issued.record.user_id == 42
    assert issued.record.token_hash == sha256(issued.token.encode()).hexdigest()
    assert issued.record.token_hash != issued.token
    assert issued.record.token_prefix == issued.token[:12]
    assert issued.record.scopes == ["today:read", "sleep:read"]
    db.add.assert_called_once_with(issued.record)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(issued.record)


@pytest.mark.asyncio
async def test_authenticate_resolves_token_owned_user_and_records_use() -> None:
    db = _db()
    token_id = uuid4()
    row = AgentToken(
        id=token_id,
        user_id=42,
        name="Hermes",
        token_prefix="lstm_example",
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

    principal = await AgentTokenService(db).authenticate("lstm_a-valid-looking-secret")

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

    with pytest.raises(AuthenticationError, match="Invalid agent token"):
        await AgentTokenService(db).authenticate("lstm_unknown")

    expired = AgentToken(
        id=uuid4(),
        user_id=42,
        name="Old",
        token_prefix="lstm_expired",
        token_hash="stored",
        scopes=["today:read"],
        expires_at=utc_now() - timedelta(seconds=1),
    )
    db.scalar.return_value = expired
    with pytest.raises(AuthenticationError, match="Invalid agent token"):
        await AgentTokenService(db).authenticate("lstm_expired-secret")

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_is_scoped_to_browser_user() -> None:
    db = _db()
    db.scalar.return_value = None

    with pytest.raises(NotFoundError, match="Agent token not found"):
        await AgentTokenService(db).revoke(user_id=42, token_id=uuid4())

    db.commit.assert_not_awaited()


def test_token_request_requires_explicit_valid_scopes_and_aware_expiry() -> None:
    with pytest.raises(ValidationError):
        AgentTokenCreate(name="Hermes", scopes=[])
    with pytest.raises(ValidationError):
        AgentTokenCreate(
            name="Hermes",
            scopes=[AgentScope.TODAY_READ],
            expires_at=(utc_now() + timedelta(days=1)).replace(tzinfo=None),
        )

    payload = AgentTokenCreate(
        name=" Hermes ",
        scopes=[AgentScope.TODAY_READ, AgentScope.TODAY_READ],
    )
    assert payload.name == "Hermes"
    assert payload.scopes == [AgentScope.TODAY_READ]


@pytest.mark.asyncio
async def test_issued_token_response_is_not_cacheable() -> None:
    issued = IssuedAgentToken(
        token="lstm_secret",
        record=AgentToken(
            id=uuid4(),
            user_id=42,
            name="Hermes",
            token_prefix="lstm_secret",
            token_hash="digest",
            scopes=["today:read"],
            created_at=utc_now(),
        ),
    )
    response = Response()
    principal = Principal(user_id=42, email="owner@example.com", session_id=uuid4())
    with patch.object(AgentTokenService, "create", AsyncMock(return_value=issued)):
        result = await create_agent_token(
            AgentTokenCreate(name="Hermes", scopes=[AgentScope.TODAY_READ]),
            response,
            principal,
            _db(),
        )

    assert response.headers["cache-control"] == "no-store"
    assert result.token == "lstm_secret"
