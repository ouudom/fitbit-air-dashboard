import secrets
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.errors import AuthenticationError, ConflictError, NotFoundError
from src.core.security import hash_password, verify_password
from src.core.time import utc_now
from src.modules.identity.models import AdminAccount, AppSession, User


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    user: User


class IdentityService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def setup(self, supplied_token: str, email: str, password: str) -> IssuedSession:
        count = await self.db.scalar(select(func.count()).select_from(AdminAccount))
        if count:
            raise NotFoundError("Setup unavailable")
        if not self.settings.setup_token or not secrets.compare_digest(
            supplied_token, self.settings.setup_token
        ):
            raise AuthenticationError("Invalid setup token")
        normalized = email.lower().strip()
        user = await self.db.scalar(select(User).where(User.email == normalized))
        if user is None:
            user = User(email=normalized, password=hash_password(password), name="Admin")
            self.db.add(user)
        else:
            user.password = hash_password(password)
        try:
            await self.db.flush()
            self.db.add(AdminAccount(id=1, user_id=user.id))
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("Setup already completed") from exc
        return await self._issue(user)

    async def login(self, email: str, password: str) -> IssuedSession:
        user = await self.db.scalar(
            select(User)
            .join(AdminAccount, AdminAccount.user_id == User.id)
            .where(User.email == email.lower().strip())
        )
        if user is None or not verify_password(password, user.password):
            raise AuthenticationError("Invalid email or password")
        return await self._issue(user)

    async def logout(self, token: str | None) -> None:
        if token:
            row = await self.db.scalar(
                select(AppSession).where(
                    AppSession.token_hash == sha256(token.encode()).hexdigest()
                )
            )
            if row:
                await self.db.delete(row)
                await self.db.commit()

    async def _issue(self, user: User) -> IssuedSession:
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        row = AppSession(
            user_id=user.id,
            token_hash=sha256(token.encode()).hexdigest(),
            csrf_token_hash=sha256(csrf.encode()).hexdigest(),
            expires_at=utc_now() + timedelta(hours=self.settings.session_lifetime_hours),
        )
        self.db.add(row)
        await self.db.commit()
        return IssuedSession(token, csrf, user)
