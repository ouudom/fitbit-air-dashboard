import base64
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Update

from src.core.errors import AuthenticationError, NotFoundError
from src.core.time import utc_now
from src.modules.agent_access.models import (
    AgentOAuthClient,
    AgentOAuthCredential,
    AgentOAuthGrant,
    OAuthCredentialKind,
)
from src.modules.agent_access.schemas import AgentScope
from src.modules.auth.models import User

OAUTH_CLIENT_ID_PREFIX = "lso_"
OAUTH_ACCESS_TOKEN_PREFIX = "lsoa_"
OAUTH_REFRESH_TOKEN_PREFIX = "lsor_"
OAUTH_ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
OAUTH_AUTHORIZATION_CODE_LIFETIME = timedelta(minutes=5)
OAUTH_REFRESH_TOKEN_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class AgentPrincipal:
    user_id: int
    token_id: UUID
    scopes: frozenset[AgentScope]

    def has_scope(self, scope: AgentScope) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class IssuedOAuthAccessToken:
    access_token: str
    scopes: tuple[AgentScope, ...]
    expires_in: int
    refresh_token: str | None = None


@dataclass(frozen=True)
class AgentOAuthGrantView:
    id: UUID
    client_id: str
    client_name: str
    scopes: list[str]
    resource: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvalidOAuthScopeError(ValueError):
    pass


class InvalidOAuthGrantError(ValueError):
    pass


class InvalidOAuthClientError(ValueError):
    pass


class AgentOAuthClientService:
    """OAuth persistence for public PKCE clients and per-user grants."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_client(
        self,
        *,
        client_name: str,
        redirect_uris: list[str],
    ) -> AgentOAuthClient:
        normalized_uris = list(dict.fromkeys(redirect_uris))
        if not client_name.strip() or not normalized_uris:
            raise InvalidOAuthClientError("Client name and redirect URIs are required")
        row = AgentOAuthClient(
            client_id=f"{OAUTH_CLIENT_ID_PREFIX}{secrets.token_urlsafe(24)}",
            client_name=client_name.strip(),
            redirect_uris=normalized_uris,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_client(self, client_id: str) -> AgentOAuthClient:
        row = await self.db.scalar(
            select(AgentOAuthClient).where(
                AgentOAuthClient.client_id == client_id,
                AgentOAuthClient.revoked_at.is_(None),
            )
        )
        if row is None:
            raise InvalidOAuthClientError("OAuth client is invalid")
        return row

    async def create_or_update_grant(
        self,
        user_id: int,
        *,
        client_id: str,
        scopes: list[str],
        resource: str,
    ) -> AgentOAuthGrant:
        client = await self.get_client(client_id)
        requested = _validated_scopes(scopes)
        if not resource:
            raise InvalidOAuthGrantError("Protected resource is required")
        if await self.db.get(User, user_id) is None:
            raise AuthenticationError("Account unavailable")
        await self.db.scalar(
            select(AgentOAuthClient).where(AgentOAuthClient.id == client.id).with_for_update()
        )
        grant = await self.db.scalar(
            select(AgentOAuthGrant).where(
                AgentOAuthGrant.oauth_client_id == client.id,
                AgentOAuthGrant.user_id == user_id,
                AgentOAuthGrant.resource == resource,
            )
        )
        now = utc_now()
        if grant is None:
            grant = AgentOAuthGrant(
                oauth_client_id=client.id,
                user_id=user_id,
                scopes=requested,
                resource=resource,
            )
            self.db.add(grant)
        else:
            if grant.revoked_at is not None or set(grant.scopes) != set(requested):
                await self.db.execute(
                    _active_credentials_for_grant(grant.id).values(revoked_at=now)
                )
            grant.scopes = requested
            grant.revoked_at = None
            grant.last_used_at = now
        await self.db.commit()
        await self.db.refresh(grant)
        return grant

    async def list_grants(self, user_id: int) -> list[AgentOAuthGrantView]:
        result = await self.db.execute(
            select(AgentOAuthGrant, AgentOAuthClient)
            .join(AgentOAuthClient, AgentOAuthClient.id == AgentOAuthGrant.oauth_client_id)
            .where(AgentOAuthGrant.user_id == user_id)
            .order_by(AgentOAuthGrant.created_at.desc())
        )
        return [
            AgentOAuthGrantView(
                id=grant.id,
                client_id=client.client_id,
                client_name=client.client_name,
                scopes=list(grant.scopes),
                resource=grant.resource,
                last_used_at=grant.last_used_at,
                revoked_at=grant.revoked_at,
                created_at=grant.created_at,
            )
            for grant, client in result.all()
        ]

    async def revoke_grant(self, user_id: int, grant_id: UUID) -> None:
        grant = await self.db.scalar(
            select(AgentOAuthGrant).where(
                AgentOAuthGrant.id == grant_id,
                AgentOAuthGrant.user_id == user_id,
            )
        )
        if grant is None:
            raise NotFoundError("OAuth grant not found")
        if grant.revoked_at is None:
            now = utc_now()
            grant.revoked_at = now
            await self.db.execute(_active_credentials_for_grant(grant.id).values(revoked_at=now))
            await self.db.commit()

    async def issue_authorization_code(
        self,
        *,
        user_id: int,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        requested_scopes: list[str],
        resource: str,
    ) -> str:
        client = await self.get_client(client_id)
        if redirect_uri not in client.redirect_uris:
            raise InvalidOAuthGrantError("Redirect URI is not registered")
        if not _is_s256_challenge(code_challenge):
            raise InvalidOAuthGrantError("PKCE S256 challenge is required")
        if not resource:
            raise InvalidOAuthGrantError("Protected resource is required")
        grant = await self.create_or_update_grant(
            user_id,
            client_id=client_id,
            scopes=requested_scopes,
            resource=resource,
        )
        raw_code = secrets.token_urlsafe(48)
        self.db.add(
            AgentOAuthCredential(
                grant_id=grant.id,
                kind=OAuthCredentialKind.AUTHORIZATION_CODE.value,
                value_hash=_token_digest(raw_code),
                scopes=list(grant.scopes),
                redirect_uri=redirect_uri,
                code_challenge=code_challenge,
                expires_at=utc_now() + OAUTH_AUTHORIZATION_CODE_LIFETIME,
            )
        )
        await self.db.commit()
        return raw_code

    async def exchange_authorization_code(
        self,
        *,
        client_id: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
        resource: str,
    ) -> IssuedOAuthAccessToken:
        now = utc_now()
        client = await self.get_client(client_id)
        result = await self.db.execute(
            select(AgentOAuthCredential, AgentOAuthGrant)
            .join(AgentOAuthGrant, AgentOAuthGrant.id == AgentOAuthCredential.grant_id)
            .where(
                AgentOAuthGrant.oauth_client_id == client.id,
                AgentOAuthGrant.resource == resource,
                AgentOAuthGrant.revoked_at.is_(None),
                AgentOAuthCredential.kind == OAuthCredentialKind.AUTHORIZATION_CODE.value,
                AgentOAuthCredential.value_hash == _token_digest(code),
                AgentOAuthCredential.consumed_at.is_(None),
                AgentOAuthCredential.revoked_at.is_(None),
                AgentOAuthCredential.expires_at > now,
            )
            .with_for_update()
        )
        pair = result.one_or_none()
        if pair is None:
            raise InvalidOAuthGrantError("Authorization code is invalid or expired")
        code_row, grant = pair
        if (
            code_row.redirect_uri != redirect_uri
            or code_row.code_challenge is None
            or not compare_digest(code_row.code_challenge, _pkce_challenge(code_verifier))
        ):
            raise InvalidOAuthGrantError("Authorization code is invalid or expired")
        code_row.consumed_at = now
        grant.last_used_at = now
        access_token = self._new_credential(
            grant.id,
            OAuthCredentialKind.ACCESS_TOKEN,
            OAUTH_ACCESS_TOKEN_PREFIX,
            list(code_row.scopes),
            OAUTH_ACCESS_TOKEN_LIFETIME,
        )
        refresh_token = self._new_credential(
            grant.id,
            OAuthCredentialKind.REFRESH_TOKEN,
            OAUTH_REFRESH_TOKEN_PREFIX,
            list(code_row.scopes),
            OAUTH_REFRESH_TOKEN_LIFETIME,
        )
        await self._purge_expired_credentials(now)
        await self.db.commit()
        scopes = tuple(AgentScope(value) for value in code_row.scopes)
        return IssuedOAuthAccessToken(
            access_token,
            scopes,
            int(OAUTH_ACCESS_TOKEN_LIFETIME.total_seconds()),
            refresh_token,
        )

    async def refresh_access_token(
        self,
        *,
        client_id: str,
        refresh_token: str,
        requested_scopes: list[str],
        resource: str,
    ) -> IssuedOAuthAccessToken:
        now = utc_now()
        client = await self.get_client(client_id)
        result = await self.db.execute(
            select(AgentOAuthCredential, AgentOAuthGrant)
            .join(AgentOAuthGrant, AgentOAuthGrant.id == AgentOAuthCredential.grant_id)
            .where(
                AgentOAuthGrant.oauth_client_id == client.id,
                AgentOAuthGrant.resource == resource,
                AgentOAuthGrant.revoked_at.is_(None),
                AgentOAuthCredential.kind == OAuthCredentialKind.REFRESH_TOKEN.value,
                AgentOAuthCredential.value_hash == _token_digest(refresh_token),
                AgentOAuthCredential.consumed_at.is_(None),
                AgentOAuthCredential.revoked_at.is_(None),
                AgentOAuthCredential.expires_at > now,
            )
            .with_for_update()
        )
        pair = result.one_or_none()
        if pair is None:
            await self._revoke_refresh_family_on_reuse(
                client.id,
                refresh_token=refresh_token,
                resource=resource,
                now=now,
            )
            raise InvalidOAuthGrantError("Refresh token is invalid or expired")
        credential, grant = pair
        requested = (
            _validated_scopes(requested_scopes) if requested_scopes else list(credential.scopes)
        )
        if not set(requested).issubset(set(credential.scopes)):
            raise InvalidOAuthScopeError("Requested scope exceeds original grant")

        credential.consumed_at = now
        credential.last_used_at = now
        grant.last_used_at = now
        access_token = self._new_credential(
            grant.id,
            OAuthCredentialKind.ACCESS_TOKEN,
            OAUTH_ACCESS_TOKEN_PREFIX,
            requested,
            OAUTH_ACCESS_TOKEN_LIFETIME,
        )
        rotated_refresh_token = self._new_credential(
            grant.id,
            OAuthCredentialKind.REFRESH_TOKEN,
            OAUTH_REFRESH_TOKEN_PREFIX,
            requested,
            OAUTH_REFRESH_TOKEN_LIFETIME,
        )
        await self._purge_expired_credentials(now)
        await self.db.commit()
        return IssuedOAuthAccessToken(
            access_token,
            tuple(AgentScope(value) for value in requested),
            int(OAUTH_ACCESS_TOKEN_LIFETIME.total_seconds()),
            rotated_refresh_token,
        )

    async def authenticate_access_token(
        self,
        raw_token: str,
        *,
        expected_resource: str | None = None,
    ) -> AgentPrincipal:
        if not raw_token.startswith(OAUTH_ACCESS_TOKEN_PREFIX):
            raise AuthenticationError("Invalid OAuth access token")
        now = utc_now()
        result = await self.db.execute(
            select(AgentOAuthCredential, AgentOAuthGrant, AgentOAuthClient)
            .join(AgentOAuthGrant, AgentOAuthGrant.id == AgentOAuthCredential.grant_id)
            .join(AgentOAuthClient, AgentOAuthClient.id == AgentOAuthGrant.oauth_client_id)
            .where(
                AgentOAuthCredential.kind == OAuthCredentialKind.ACCESS_TOKEN.value,
                AgentOAuthCredential.value_hash == _token_digest(raw_token),
                AgentOAuthCredential.expires_at > now,
                AgentOAuthCredential.consumed_at.is_(None),
                AgentOAuthCredential.revoked_at.is_(None),
                AgentOAuthGrant.revoked_at.is_(None),
                AgentOAuthClient.revoked_at.is_(None),
            )
        )
        triple = result.one_or_none()
        if triple is None:
            raise AuthenticationError("Invalid OAuth access token")
        credential, grant, _client = triple
        if expected_resource is not None and grant.resource != expected_resource:
            raise AuthenticationError("OAuth access token has invalid audience")
        if await self.db.get(User, grant.user_id) is None:
            raise AuthenticationError("Account unavailable")
        credential.last_used_at = now
        grant.last_used_at = now
        await self.db.commit()
        try:
            scopes = frozenset(AgentScope(value) for value in credential.scopes)
        except ValueError as exc:
            raise AuthenticationError("Invalid OAuth access token scopes") from exc
        return AgentPrincipal(grant.user_id, credential.id, scopes)

    async def revoke_token(self, raw_token: str, *, client_id: str) -> None:
        client = await self.get_client(client_id)
        result = await self.db.execute(
            select(AgentOAuthCredential)
            .join(AgentOAuthGrant, AgentOAuthGrant.id == AgentOAuthCredential.grant_id)
            .where(
                AgentOAuthGrant.oauth_client_id == client.id,
                AgentOAuthCredential.value_hash == _token_digest(raw_token),
                AgentOAuthCredential.revoked_at.is_(None),
            )
        )
        credential = result.scalar_one_or_none()
        if credential is not None:
            credential.revoked_at = utc_now()
            await self.db.commit()

    def _new_credential(
        self,
        grant_id: UUID,
        kind: OAuthCredentialKind,
        prefix: str,
        scopes: list[str],
        lifetime: timedelta,
    ) -> str:
        raw_value = f"{prefix}{secrets.token_urlsafe(48)}"
        self.db.add(
            AgentOAuthCredential(
                grant_id=grant_id,
                kind=kind.value,
                value_hash=_token_digest(raw_value),
                scopes=scopes,
                expires_at=utc_now() + lifetime,
            )
        )
        return raw_value

    async def _purge_expired_credentials(self, now: datetime) -> None:
        await self.db.execute(
            delete(AgentOAuthCredential).where(AgentOAuthCredential.expires_at <= now)
        )

    async def _revoke_refresh_family_on_reuse(
        self,
        oauth_client_id: UUID,
        *,
        refresh_token: str,
        resource: str,
        now: datetime,
    ) -> None:
        result = await self.db.execute(
            select(AgentOAuthCredential)
            .join(AgentOAuthGrant, AgentOAuthGrant.id == AgentOAuthCredential.grant_id)
            .where(
                AgentOAuthGrant.oauth_client_id == oauth_client_id,
                AgentOAuthGrant.resource == resource,
                AgentOAuthCredential.kind == OAuthCredentialKind.REFRESH_TOKEN.value,
                AgentOAuthCredential.value_hash == _token_digest(refresh_token),
                AgentOAuthCredential.consumed_at.is_not(None),
            )
        )
        reused = result.scalar_one_or_none()
        if reused is not None:
            await self.db.execute(
                _active_credentials_for_grant(reused.grant_id).values(revoked_at=now)
            )
            await self.db.commit()


def _active_credentials_for_grant(grant_id: UUID) -> Update:
    return update(AgentOAuthCredential).where(
        AgentOAuthCredential.grant_id == grant_id,
        AgentOAuthCredential.revoked_at.is_(None),
    )


def _validated_scopes(scopes: list[str]) -> list[str]:
    requested = list(dict.fromkeys(scopes))
    if not requested:
        raise InvalidOAuthScopeError("At least one scope is required")
    try:
        for value in requested:
            AgentScope(value)
    except ValueError as exc:
        raise InvalidOAuthScopeError("Requested scope is unknown") from exc
    return requested


def _token_digest(raw_token: str) -> str:
    return sha256(raw_token.encode()).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")


def _is_s256_challenge(challenge: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge) is not None
