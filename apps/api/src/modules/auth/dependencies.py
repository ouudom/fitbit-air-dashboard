from collections.abc import AsyncIterator
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_scope
from src.core.time import utc_now
from src.modules.auth.models import Session, User


@dataclass(frozen=True)
class Principal:
    user_id: int
    email: str
    session_id: UUID


async def database_session() -> AsyncIterator[AsyncSession]:
    async for session in session_scope():
        yield session


async def current_principal(
    request: Request,
    session_token: str | None = Cookie(default=None, alias="lifestats_session"),
    db: AsyncSession = Depends(database_session),
) -> Principal:
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    digest = sha256(session_token.encode()).hexdigest()
    row = await db.scalar(
        select(Session).where(
            Session.token_hash == digest,
            Session.expires_at > utc_now(),
            Session.revoked_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account unavailable")
    request.state.app_session = row
    return Principal(user.id, user.email, row.id)


async def require_csrf(
    request: Request,
    principal: Principal = Depends(current_principal),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(default=None, alias="lifestats_csrf"),
) -> Principal:
    row: Session = request.state.app_session
    if not csrf_header or not csrf_cookie or not compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token")
    if not compare_digest(sha256(csrf_header.encode()).hexdigest(), row.csrf_token_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token")
    return principal
