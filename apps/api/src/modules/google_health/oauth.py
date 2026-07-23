import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.time import utc_now
from src.modules.google_health.client import GoogleHealthClient
from src.modules.google_health.crypto import TokenCipher
from src.modules.google_health.models import GoogleHealthConnection
from src.modules.google_health.oauth_state import OAuthStateStore, RedisOAuthStateStore
from src.modules.google_health.sync import seed_sync_jobs


class OAuthService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        state_store: OAuthStateStore | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.state_store = state_store or RedisOAuthStateStore(settings.redis_url)
        self.cipher = TokenCipher(
            settings.token_encryption_key,
            settings.app_key,
            settings.google_client_secret,
        )

    async def authorization_url(self, user_id: int) -> str:
        state = secrets.token_urlsafe(32)
        await self.state_store.issue(state, user_id)
        return (
            self.settings.google_auth_url
            + "?"
            + urlencode(
                {
                    "client_id": self.settings.google_client_id,
                    "redirect_uri": self.settings.redirect_uri,
                    "response_type": "code",
                    "access_type": "offline",
                    "prompt": "consent",
                    "include_granted_scopes": "true",
                    "scope": self.settings.scopes,
                    "state": state,
                }
            )
        )

    async def callback(self, state: str, code: str) -> int:
        user_id = await self.state_store.consume(state)
        if user_id is None:
            raise ValueError("Invalid OAuth state")
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                self.settings.google_token_url,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()
        existing = await self.db.scalar(
            select(GoogleHealthConnection).where(GoogleHealthConnection.user_id == user_id)
        )
        connection = existing or GoogleHealthConnection(
            user_id=user_id,
            access_token_ciphertext="",
        )
        connection.access_token_ciphertext = self.cipher.encrypt(data["access_token"]) or ""
        if data.get("refresh_token"):
            connection.refresh_token_ciphertext = self.cipher.encrypt(data["refresh_token"])
        connection.token_expires_at = utc_now() + timedelta(
            seconds=int(data.get("expires_in", 3600))
        )
        scope = data.get("scope")
        if isinstance(scope, str):
            connection.scopes = scope.split()
        if existing is None:
            self.db.add(connection)
        await self.db.flush()
        client = GoogleHealthClient(self.db, self.settings, user_id)
        try:
            identity = await client.request("GET", "users/me/identity")
        finally:
            await client.close()
        health_user_id = str(identity.get("healthUserId", ""))
        if not health_user_id:
            raise RuntimeError("Google Health identity missing")
        connection.provider_user_id = health_user_id
        connection.last_verified_at = utc_now()
        connection.status = "active"
        await self.db.commit()
        await seed_sync_jobs(self.db, connection)
        return user_id

    async def revoke_token(self, connection: GoogleHealthConnection) -> None:
        token = self.cipher.decrypt(connection.refresh_token_ciphertext) or self.cipher.decrypt(
            connection.access_token_ciphertext
        )
        if not token:
            return
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                self.settings.google_revoke_url,
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code == 400:
            return
        response.raise_for_status()
