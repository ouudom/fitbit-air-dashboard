from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.dependencies import database_session
from src.core.errors import NotFoundError
from src.modules.agent_access.schemas import (
    AgentOAuthGrantResponse,
    AgentScope,
    OAuthAuthorizationDecisionRequest,
    OAuthAuthorizationDecisionResponse,
    OAuthAuthorizationPreviewResponse,
)
from src.modules.agent_access.service import (
    AgentOAuthClientService,
    InvalidOAuthClientError,
    InvalidOAuthGrantError,
    InvalidOAuthScopeError,
)
from src.modules.auth.dependencies import Principal, current_principal, require_csrf

oauth_router = APIRouter(tags=["Agent OAuth"])

DEFAULT_AGENT_SCOPES = [
    AgentScope.PROFILE_READ,
    AgentScope.TODAY_READ,
    AgentScope.FITNESS_READ,
    AgentScope.SLEEP_READ,
    AgentScope.HEALTH_READ,
    AgentScope.NUTRITION_READ,
    AgentScope.SYNC_READ,
    AgentScope.INTEGRATION_READ,
]


def _parse_scopes(value: str) -> list[AgentScope]:
    values = value.split() if value else [scope.value for scope in DEFAULT_AGENT_SCOPES]
    if len(values) != len(set(values)):
        values = list(dict.fromkeys(values))
    try:
        return [AgentScope(scope) for scope in values]
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported OAuth scope") from exc


def _redirect_with_parameters(uri: str, parameters: dict[str, str | None]) -> str:
    split = urlsplit(uri)
    query = parse_qsl(split.query, keep_blank_values=True)
    query.extend((key, value) for key, value in parameters.items() if value is not None)
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


async def _validate_authorization_request(
    service: AgentOAuthClientService,
    *,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    code_challenge: str,
    code_challenge_method: str,
    scope: str,
    resource: str,
    settings: Settings,
) -> tuple[str, list[AgentScope]]:
    if response_type != "code":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "response_type must be code")
    if code_challenge_method != "S256" or not code_challenge:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "PKCE S256 challenge is required")
    if resource != settings.mcp_public_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid protected resource")
    try:
        client = await service.get_client(client_id)
    except InvalidOAuthClientError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Redirect URI is not registered")
    return client.client_name, _parse_scopes(scope)


@oauth_router.get(
    "/oauth/authorize/preview",
    response_model=OAuthAuthorizationPreviewResponse,
)
async def preview_authorization(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    client_id: Annotated[str, Query(min_length=1)],
    redirect_uri: Annotated[str, Query(min_length=1)],
    response_type: str,
    code_challenge: Annotated[str, Query(min_length=1)],
    code_challenge_method: str,
    resource: Annotated[str, Query(min_length=1)],
    scope: str = "",
    state: str | None = None,
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> OAuthAuthorizationPreviewResponse:
    del principal, state
    if any(
        len(request.query_params.getlist(name)) > 1
        for name in (
            "client_id",
            "redirect_uri",
            "response_type",
            "code_challenge",
            "code_challenge_method",
            "scope",
            "resource",
            "state",
        )
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Duplicate OAuth parameter")
    client_name, scopes = await _validate_authorization_request(
        AgentOAuthClientService(db),
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        scope=scope,
        resource=resource,
        settings=settings,
    )
    return OAuthAuthorizationPreviewResponse(
        client_id=client_id,
        client_name=client_name,
        redirect_uri=redirect_uri,
        scopes=scopes,
        resource=resource,
    )


@oauth_router.post(
    "/oauth/authorize/decision",
    response_model=OAuthAuthorizationDecisionResponse,
)
async def decide_authorization(
    payload: OAuthAuthorizationDecisionRequest,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> OAuthAuthorizationDecisionResponse:
    service = AgentOAuthClientService(db)
    _, scopes = await _validate_authorization_request(
        service,
        client_id=payload.client_id,
        redirect_uri=payload.redirect_uri,
        response_type=payload.response_type,
        code_challenge=payload.code_challenge,
        code_challenge_method=payload.code_challenge_method,
        scope=payload.scope,
        resource=payload.resource,
        settings=settings,
    )
    issuer = settings.mcp_oauth_issuer_url.rstrip("/")
    if not payload.approved:
        return OAuthAuthorizationDecisionResponse(
            redirect_to=_redirect_with_parameters(
                payload.redirect_uri,
                {"error": "access_denied", "state": payload.state, "iss": issuer},
            )
        )
    try:
        code = await service.issue_authorization_code(
            user_id=principal.user_id,
            client_id=payload.client_id,
            redirect_uri=payload.redirect_uri,
            code_challenge=payload.code_challenge,
            requested_scopes=[scope.value for scope in scopes],
            resource=payload.resource,
        )
    except (InvalidOAuthClientError, InvalidOAuthGrantError, InvalidOAuthScopeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return OAuthAuthorizationDecisionResponse(
        redirect_to=_redirect_with_parameters(
            payload.redirect_uri,
            {"code": code, "state": payload.state, "iss": issuer},
        )
    )


@oauth_router.get("/oauth-grants", response_model=list[AgentOAuthGrantResponse])
async def list_oauth_grants(
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> list[AgentOAuthGrantResponse]:
    rows = await AgentOAuthClientService(db).list_grants(principal.user_id)
    return [AgentOAuthGrantResponse.model_validate(row, from_attributes=True) for row in rows]


@oauth_router.delete("/oauth-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_oauth_grant(
    grant_id: UUID,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> None:
    try:
        await AgentOAuthClientService(db).revoke_grant(principal.user_id, grant_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
