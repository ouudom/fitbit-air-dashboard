import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from time import monotonic

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.errors import AuthenticationError, ConflictError, NotFoundError, RateLimitedError
from src.core.security import hash_password, verify_password
from src.core.time import utc_now
from src.modules.auth.models import Session, User

_LOGIN_FAILURE_LIMIT = 5
_LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60
_login_failures: dict[str, deque[float]] = defaultdict(deque)


def _login_rate_limited(key: str) -> bool:
    now = monotonic()
    cutoff = now - _LOGIN_FAILURE_WINDOW_SECONDS
    attempts = _login_failures[key]
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()
    return len(attempts) >= _LOGIN_FAILURE_LIMIT


def _record_login_failure(key: str) -> None:
    _login_failures[key].append(monotonic())


def _clear_login_failures(key: str) -> None:
    _login_failures.pop(key, None)


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    user: User


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def setup(self, supplied_token: str, email: str, password: str) -> IssuedSession:
        count = await self.db.scalar(select(func.count()).select_from(User))
        if count:
            raise NotFoundError("Setup unavailable")
        if not self.settings.setup_token or not secrets.compare_digest(
            supplied_token, self.settings.setup_token
        ):
            raise AuthenticationError("Invalid setup token")
        normalized = email.lower().strip()
        user = await self.db.scalar(select(User).where(User.email == normalized))
        if user is None:
            user = User(
                email=normalized,
                password_hash=hash_password(password),
                name="Admin",
            )
            self.db.add(user)
        else:
            user.password_hash = hash_password(password)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("Setup already completed") from exc
        return await self._issue(user)

    async def login(self, email: str, password: str) -> IssuedSession:
        normalized = email.lower().strip()
        if _login_rate_limited(normalized):
            raise RateLimitedError("Too many failed login attempts. Try again later.")
        user = await self.db.scalar(select(User).where(User.email == normalized))
        if user is None or not verify_password(password, user.password_hash):
            _record_login_failure(normalized)
            raise AuthenticationError("Invalid email or password")
        _clear_login_failures(normalized)
        return await self._issue(user)

    async def logout(self, token: str | None) -> None:
        if token:
            row = await self.db.scalar(
                select(Session).where(Session.token_hash == sha256(token.encode()).hexdigest())
            )
            if row:
                await self.db.delete(row)
                await self.db.commit()

    async def _issue(self, user: User) -> IssuedSession:
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        row = Session(
            user_id=user.id,
            token_hash=sha256(token.encode()).hexdigest(),
            csrf_token_hash=sha256(csrf.encode()).hexdigest(),
            expires_at=utc_now() + timedelta(hours=self.settings.session_lifetime_hours),
        )
        self.db.add(row)
        await self.db.commit()
        return IssuedSession(token, csrf, user)
