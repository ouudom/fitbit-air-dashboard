import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AuthenticationError, NotFoundError
from src.core.time import utc_now
from src.modules.agent_access.models import McpToken
from src.modules.agent_access.schemas import AgentScope
from src.modules.auth.models import User

TOKEN_PREFIX = "lsmcp_"
LAST_USED_WRITE_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class AgentPrincipal:
    user_id: int
    token_id: UUID
    scopes: frozenset[AgentScope]

    def has_scope(self, scope: AgentScope) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class IssuedMcpToken:
    token: str
    record: McpToken


class McpTokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: int,
        *,
        name: str,
        scopes: list[AgentScope],
        expires_at: datetime | None,
    ) -> IssuedMcpToken:
        raw_token = f"{TOKEN_PREFIX}{secrets.token_urlsafe(48)}"
        row = McpToken(
            user_id=user_id,
            name=name,
            token_prefix=raw_token[:16],
            token_hash=_token_digest(raw_token),
            scopes=[scope.value for scope in scopes],
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return IssuedMcpToken(raw_token, row)

    async def list(self, user_id: int) -> list[McpToken]:
        rows = await self.db.scalars(
            select(McpToken).where(McpToken.user_id == user_id).order_by(McpToken.created_at.desc())
        )
        return list(rows)

    async def revoke(self, user_id: int, token_id: UUID) -> None:
        row = await self.db.scalar(
            select(McpToken).where(
                McpToken.id == token_id,
                McpToken.user_id == user_id,
            )
        )
        if row is None:
            raise NotFoundError("MCP token not found")
        if row.revoked_at is None:
            row.revoked_at = utc_now()
            await self.db.commit()

    async def authenticate(self, raw_token: str) -> AgentPrincipal:
        if not raw_token.startswith(("lsmcp_", "lstm_")):
            raise AuthenticationError("Invalid MCP token")
        now = utc_now()
        row = await self.db.scalar(
            select(McpToken).where(
                McpToken.token_hash == _token_digest(raw_token),
                McpToken.revoked_at.is_(None),
            )
        )
        if row is None or (row.expires_at is not None and row.expires_at <= now):
            raise AuthenticationError("Invalid MCP token")
        if await self.db.get(User, row.user_id) is None:
            raise AuthenticationError("Account unavailable")
        if row.last_used_at is None or row.last_used_at <= now - LAST_USED_WRITE_INTERVAL:
            row.last_used_at = now
            await self.db.commit()
        try:
            scopes = frozenset(AgentScope(value) for value in row.scopes)
        except ValueError as exc:
            raise AuthenticationError("Invalid MCP token scopes") from exc
        return AgentPrincipal(row.user_id, row.id, scopes)


def _token_digest(raw_token: str) -> str:
    return sha256(raw_token.encode()).hexdigest()
