import secrets
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AuthenticationError, NotFoundError
from src.core.time import utc_now
from src.modules.agent_access.models import AgentToken
from src.modules.agent_access.schemas import AgentScope
from src.modules.auth.models import User

TOKEN_PREFIX = "lstm_"


@dataclass(frozen=True)
class AgentPrincipal:
    user_id: int
    token_id: UUID
    scopes: frozenset[AgentScope]

    def has_scope(self, scope: AgentScope) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class IssuedAgentToken:
    token: str
    record: AgentToken


class AgentTokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: int,
        *,
        name: str,
        scopes: list[AgentScope],
        expires_at: datetime | None,
    ) -> IssuedAgentToken:
        raw_token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(48)}"
        row = AgentToken(
            user_id=user_id,
            name=name,
            token_prefix=raw_token[:12],
            token_hash=_token_digest(raw_token),
            scopes=[scope.value for scope in scopes],
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return IssuedAgentToken(raw_token, row)

    async def list(self, user_id: int) -> list[AgentToken]:
        rows = await self.db.scalars(
            select(AgentToken)
            .where(AgentToken.user_id == user_id)
            .order_by(AgentToken.created_at.desc())
        )
        return list(rows)

    async def revoke(self, user_id: int, token_id: UUID) -> None:
        row = await self.db.scalar(
            select(AgentToken).where(
                AgentToken.id == token_id,
                AgentToken.user_id == user_id,
            )
        )
        if row is None:
            raise NotFoundError("Agent token not found")
        if row.revoked_at is None:
            row.revoked_at = utc_now()
            await self.db.commit()

    async def authenticate(self, raw_token: str) -> AgentPrincipal:
        if not raw_token.startswith(TOKEN_PREFIX):
            raise AuthenticationError("Invalid agent token")
        now = utc_now()
        row = await self.db.scalar(
            select(AgentToken).where(
                AgentToken.token_hash == _token_digest(raw_token),
                AgentToken.revoked_at.is_(None),
            )
        )
        if row is None or (row.expires_at is not None and row.expires_at <= now):
            raise AuthenticationError("Invalid agent token")
        if await self.db.get(User, row.user_id) is None:
            raise AuthenticationError("Account unavailable")
        row.last_used_at = now
        await self.db.commit()
        try:
            scopes = frozenset(AgentScope(value) for value in row.scopes)
        except ValueError as exc:
            raise AuthenticationError("Invalid agent token scopes") from exc
        return AgentPrincipal(row.user_id, row.id, scopes)


def _token_digest(raw_token: str) -> str:
    return sha256(raw_token.encode()).hexdigest()
