import json
import re
from collections import deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from datetime import date
from time import monotonic
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.config import get_settings
from src.core.database import SessionFactory
from src.core.errors import AuthenticationError
from src.modules.agent.schemas import (
    Capabilities,
    ConnectionStart,
    ConnectionStatus,
    DateRange,
    DisconnectResult,
    ExerciseExport,
    FreshnessReport,
    HealthRecord,
    Profile,
    RecordPage,
    RecordQuery,
    Summary,
    SyncCommand,
    SyncItem,
    SyncQueued,
    SyncStatus,
    Timeline,
    Today,
    Trend,
    TrendQuery,
)
from src.modules.agent.service import AgentService
from src.modules.agent_access.schemas import AgentScope
from src.modules.agent_access.service import (
    AgentOAuthClientService,
    AgentPrincipal,
    InvalidOAuthClientError,
    InvalidOAuthGrantError,
    InvalidOAuthScopeError,
)
from src.modules.google_health.registry import (
    ACTIVITY_SCOPE,
    DATA_TYPE_REGISTRY,
    ECG_SCOPE,
    HEALTH_SCOPE,
    IRN_SCOPE,
    NUTRITION_SCOPE,
    SLEEP_SCOPE,
)

_principal: ContextVar[AgentPrincipal | None] = ContextVar("mcp_principal", default=None)
_registration_attempts: deque[float] = deque()
_REGISTRATION_LIMIT = 30
_REGISTRATION_WINDOW_SECONDS = 60
_REGISTRATION_BODY_LIMIT = 16 * 1024

mcp = FastMCP(
    "LifeStats",
    instructions=(
        "Private, user-scoped Google Health companion. Results are synced projections; "
        "their source, freshness, availability, and derivation fields must be preserved."
    ),
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["mcp:*", "localhost:*", "127.0.0.1:*", "[::1]:*"],
        allowed_origins=[],
    ),
)


def _current_principal() -> AgentPrincipal:
    principal = _principal.get()
    if principal is None:
        raise ToolError("Agent authentication context is unavailable")
    return principal


def _require_scope(principal: AgentPrincipal, scope: AgentScope) -> None:
    if not principal.has_scope(scope):
        raise ToolError(f"OAuth credential lacks required scope: {scope.value}")


async def _run[T](
    scope: AgentScope,
    operation: Callable[[AgentService, int], Awaitable[T]],
) -> T:
    principal = _current_principal()
    _require_scope(principal, scope)
    async with SessionFactory() as db:
        service = AgentService(db, get_settings())
        return await operation(service, principal.user_id)


def _require_query_scopes(principal: AgentPrincipal, data_types: list[str] | None) -> None:
    selected = data_types or list(DATA_TYPE_REGISTRY)
    unknown = set(selected) - DATA_TYPE_REGISTRY.keys()
    if unknown:
        raise ToolError(f"Unsupported Google Health data type: {', '.join(sorted(unknown))}")
    scope_map = {
        ACTIVITY_SCOPE: AgentScope.FITNESS_READ,
        SLEEP_SCOPE: AgentScope.SLEEP_READ,
        HEALTH_SCOPE: AgentScope.HEALTH_READ,
        NUTRITION_SCOPE: AgentScope.NUTRITION_READ,
        ECG_SCOPE: AgentScope.ECG_READ,
        IRN_SCOPE: AgentScope.IRN_READ,
    }
    for data_type in selected:
        required = scope_map[DATA_TYPE_REGISTRY[data_type].scope]
        _require_scope(principal, required)


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/healthz", methods=["GET"], include_in_schema=False
)
async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _oauth_metadata() -> dict[str, object]:
    settings = get_settings()
    issuer = settings.mcp_oauth_issuer_url.rstrip("/")
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": [scope.value for scope in AgentScope],
    }


def _protected_resource_metadata() -> dict[str, object]:
    settings = get_settings()
    return {
        "resource": settings.mcp_public_url,
        "authorization_servers": [settings.mcp_oauth_issuer_url.rstrip("/")],
        "bearer_methods_supported": ["header"],
        "scopes_supported": [scope.value for scope in AgentScope],
    }


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/.well-known/oauth-authorization-server",
    methods=["GET"],
    include_in_schema=False,
)
async def oauth_authorization_server_metadata(_request: Request) -> JSONResponse:
    return JSONResponse(_oauth_metadata())


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/.well-known/oauth-protected-resource",
    methods=["GET"],
    include_in_schema=False,
)
async def oauth_protected_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse(_protected_resource_metadata())


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/.well-known/oauth-protected-resource/mcp",
    methods=["GET"],
    include_in_schema=False,
)
async def oauth_mcp_resource_metadata(_request: Request) -> JSONResponse:
    return JSONResponse(_protected_resource_metadata())


def _expected_resource() -> str:
    return get_settings().mcp_public_url


def _resource_parameter(form: dict[str, list[str]]) -> str | None:
    if "resource" not in form:
        return _expected_resource()
    resource = _single(form, "resource")
    return resource if resource == _expected_resource() else None


def _single(form: dict[str, list[str]], name: str) -> str | None:
    values = form.get(name)
    return values[0] if values is not None and len(values) == 1 and values[0] else None


def _valid_redirect_uri(uri: str) -> bool:
    if len(uri) > 2048 or any(character.isspace() for character in uri):
        return False
    parsed = urlsplit(uri)
    try:
        port_is_valid = parsed.port is None or parsed.port > 0
    except ValueError:
        return False
    if (
        not port_is_valid
        or not parsed.scheme
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        return False
    if parsed.scheme == "https":
        return parsed.hostname is not None
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"}


def _oauth_error(error: str, description: str, status_code: int = 400) -> JSONResponse:
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status_code,
        headers=headers,
    )


def _oauth_redirect(
    redirect_uri: str,
    *,
    error: str,
    description: str,
    state: str | None,
) -> RedirectResponse:
    parsed = urlsplit(redirect_uri)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(
        [
            ("error", error),
            ("error_description", description),
            ("iss", get_settings().mcp_oauth_issuer_url.rstrip("/")),
        ]
    )
    if state is not None:
        query.append(("state", state))
    target = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store"})


def _registration_rate_limited() -> bool:
    now = monotonic()
    cutoff = now - _REGISTRATION_WINDOW_SECONDS
    while _registration_attempts and _registration_attempts[0] <= cutoff:
        _registration_attempts.popleft()
    if len(_registration_attempts) >= _REGISTRATION_LIMIT:
        return True
    _registration_attempts.append(now)
    return False


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/oauth/register", methods=["POST"], include_in_schema=False
)
async def oauth_register(request: Request) -> JSONResponse:
    if request.headers.get("content-type", "").partition(";")[0].strip().lower() != (
        "application/json"
    ):
        return _oauth_error("invalid_client_metadata", "JSON request required")
    if _registration_rate_limited():
        return _oauth_error("temporarily_unavailable", "Registration rate limit exceeded", 429)
    try:
        raw_body = await request.body()
        if len(raw_body) > _REGISTRATION_BODY_LIMIT:
            return _oauth_error("invalid_client_metadata", "Registration request is too large")
        body = json.loads(raw_body)
    except (UnicodeDecodeError, ValueError):
        return _oauth_error("invalid_client_metadata", "Request body must be valid JSON")
    if not isinstance(body, dict):
        return _oauth_error("invalid_client_metadata", "Client metadata must be an object")

    client_name = body.get("client_name", "MCP client")
    redirect_uris = body.get("redirect_uris")
    grant_types = body.get("grant_types", ["authorization_code", "refresh_token"])
    response_types = body.get("response_types", ["code"])
    auth_method = body.get("token_endpoint_auth_method", "none")
    if not isinstance(client_name, str) or not client_name.strip() or len(client_name) > 100:
        return _oauth_error("invalid_client_metadata", "Valid client_name required")
    if (
        not isinstance(redirect_uris, list)
        or not redirect_uris
        or len(redirect_uris) > 10
        or any(not isinstance(uri, str) or not _valid_redirect_uri(uri) for uri in redirect_uris)
        or len(set(redirect_uris)) != len(redirect_uris)
    ):
        return _oauth_error("invalid_redirect_uri", "Valid unique redirect_uris required")
    if (
        not isinstance(grant_types, list)
        or any(not isinstance(value, str) for value in grant_types)
        or len(grant_types) != len(set(grant_types))
        or "authorization_code" not in grant_types
        or not set(grant_types).issubset({"authorization_code", "refresh_token"})
    ):
        return _oauth_error("invalid_client_metadata", "Unsupported grant_types")
    if response_types != ["code"] or auth_method != "none":
        return _oauth_error(
            "invalid_client_metadata",
            "Public authorization-code clients with token_endpoint_auth_method none required",
        )

    async with SessionFactory() as db:
        registration = await AgentOAuthClientService(db).register_client(
            client_name=client_name.strip(),
            redirect_uris=redirect_uris,
        )
    return JSONResponse(
        {
            "client_id": registration.client_id,
            "client_id_issued_at": int(registration.created_at.timestamp()),
            "client_name": registration.client_name,
            "redirect_uris": list(registration.redirect_uris),
            "grant_types": grant_types,
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        status_code=201,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/oauth/authorize", methods=["GET"], include_in_schema=False
)
async def oauth_authorize(request: Request) -> JSONResponse | RedirectResponse:
    query = parse_qs(request.url.query, keep_blank_values=True)
    client_id = _single(query, "client_id")
    redirect_uri = _single(query, "redirect_uri")
    if client_id is None or redirect_uri is None or not _valid_redirect_uri(redirect_uri):
        return _oauth_error("invalid_request", "Valid client_id and redirect_uri required")
    try:
        async with SessionFactory() as db:
            client = await AgentOAuthClientService(db).get_client(client_id)
    except (AuthenticationError, InvalidOAuthClientError):
        return _oauth_error("unauthorized_client", "OAuth client is unavailable")
    if redirect_uri not in client.redirect_uris:
        return _oauth_error("invalid_request", "redirect_uri is not registered")
    state_values = query.get("state", [])
    state = state_values[0] if len(state_values) == 1 else None
    code_challenge = _single(query, "code_challenge")
    resource = _resource_parameter(query)
    if (
        _single(query, "response_type") != "code"
        or code_challenge is None
        or _single(query, "code_challenge_method") != "S256"
        or re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_challenge) is None
        or resource is None
        or len(query.get("scope", [])) > 1
        or len(state_values) > 1
    ):
        return _oauth_redirect(
            redirect_uri,
            error="invalid_request",
            description="Valid code, resource, singleton scope/state, and PKCE required",
            state=state,
        )
    consent_query = request.url.query
    if "resource" not in query:
        consent_query = f"{consent_query}&{urlencode({'resource': resource})}"
    return RedirectResponse(
        f"/oauth/consent?{consent_query}",
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/oauth/token", methods=["POST"], include_in_schema=False
)
async def oauth_token(request: Request) -> JSONResponse:
    if request.headers.get("content-type", "").partition(";")[0].strip().lower() != (
        "application/x-www-form-urlencoded"
    ):
        return _oauth_error("invalid_request", "Form-encoded request required")
    try:
        form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return _oauth_error("invalid_request", "Request body must be UTF-8")
    client_id = _single(form, "client_id")
    if (
        client_id is None
        or "client_secret" in form
        or request.headers.get("authorization") is not None
    ):
        return _oauth_error("invalid_client", "Public client_id without a secret required", 401)
    grant_type = _single(form, "grant_type")
    requested_scopes = form.get("scope", [""])[0].split()
    resource = _resource_parameter(form)
    if resource is None:
        return _oauth_error("invalid_target", "Resource is not this MCP server")
    try:
        async with SessionFactory() as db:
            service = AgentOAuthClientService(db)
            if grant_type == "authorization_code":
                code = _single(form, "code")
                redirect_uri = _single(form, "redirect_uri")
                code_verifier = _single(form, "code_verifier")
                if (
                    code is None
                    or redirect_uri is None
                    or code_verifier is None
                    or re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_verifier) is None
                ):
                    return _oauth_error(
                        "invalid_request",
                        "Valid code, redirect_uri, and PKCE code_verifier required",
                    )
                issued = await service.exchange_authorization_code(
                    client_id=client_id,
                    code=code,
                    redirect_uri=redirect_uri,
                    code_verifier=code_verifier,
                    resource=resource,
                )
            elif grant_type == "refresh_token":
                refresh_token = _single(form, "refresh_token")
                if refresh_token is None:
                    return _oauth_error("invalid_request", "Refresh token is required")
                issued = await service.refresh_access_token(
                    client_id=client_id,
                    refresh_token=refresh_token,
                    requested_scopes=requested_scopes,
                    resource=resource,
                )
            else:
                return _oauth_error("unsupported_grant_type", "Grant type is not supported")
    except (AuthenticationError, InvalidOAuthClientError):
        return _oauth_error("invalid_client", "OAuth client is unavailable", 401)
    except InvalidOAuthGrantError as exc:
        return _oauth_error("invalid_grant", str(exc))
    except InvalidOAuthScopeError as exc:
        return _oauth_error("invalid_scope", str(exc))
    response_body = {
        "access_token": issued.access_token,
        "token_type": "Bearer",
        "expires_in": issued.expires_in,
        "scope": " ".join(scope.value for scope in issued.scopes),
    }
    if issued.refresh_token is not None:
        response_body["refresh_token"] = issued.refresh_token
    return JSONResponse(
        response_body,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/oauth/revoke", methods=["POST"], include_in_schema=False
)
async def oauth_revoke(request: Request) -> JSONResponse:
    if request.headers.get("content-type", "").partition(";")[0].strip().lower() != (
        "application/x-www-form-urlencoded"
    ):
        return _oauth_error("invalid_request", "Form-encoded request required")
    try:
        form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return _oauth_error("invalid_request", "Request body must be UTF-8")
    client_id = _single(form, "client_id")
    token = _single(form, "token")
    if (
        client_id is None
        or token is None
        or "client_secret" in form
        or request.headers.get("authorization") is not None
    ):
        return _oauth_error("invalid_request", "Public client_id and token required")
    try:
        async with SessionFactory() as db:
            await AgentOAuthClientService(db).revoke_token(token, client_id=client_id)
    except (AuthenticationError, InvalidOAuthClientError):
        return _oauth_error("invalid_client", "OAuth client is unavailable", 401)
    return JSONResponse(
        {},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@mcp.tool()
async def get_profile() -> Profile:
    """Return the authenticated user's display name and timezone."""
    return await _run(AgentScope.PROFILE_READ, lambda service, user: service.get_profile(user))


@mcp.tool()
async def list_capabilities() -> Capabilities:
    """List Google Health data types, grants, availability, and supported operations."""
    return await _run(
        AgentScope.PROFILE_READ, lambda service, user: service.list_capabilities(user)
    )


@mcp.tool()
async def get_google_health_status() -> ConnectionStatus:
    """Return Google Health connection and grant status."""
    return await _run(
        AgentScope.INTEGRATION_READ,
        lambda service, user: service.get_google_health_status(user),
    )


@mcp.tool()
async def get_connection_status() -> ConnectionStatus:
    """Return Google Health connection status for connection-management flows."""
    return await _run(
        AgentScope.INTEGRATION_READ,
        lambda service, user: service.get_connection_status(user),
    )


@mcp.tool()
async def start_google_health_connection() -> ConnectionStart:
    """Create a browser authorization URL for the authenticated user."""
    return await _run(
        AgentScope.INTEGRATION_WRITE,
        lambda service, user: service.start_google_health_connection(user),
    )


@mcp.tool()
async def disconnect_google_health(confirm: bool = False) -> DisconnectResult:
    """Revoke Google Health after explicit confirmation; retain the synced cache."""
    if not confirm:
        raise ToolError("Set confirm=true to disconnect Google Health")
    return await _run(
        AgentScope.INTEGRATION_WRITE,
        lambda service, user: service.disconnect_google_health(user),
    )


@mcp.tool()
async def get_data_freshness() -> FreshnessReport:
    """Return freshness and record counts for every supported Google Health type."""
    return await _run(AgentScope.SYNC_READ, lambda service, user: service.get_data_freshness(user))


@mcp.tool()
async def get_today(day: date | None = None) -> Today:
    """Return Google Health-backed Today data for one local calendar date."""
    return await _run(AgentScope.TODAY_READ, lambda service, user: service.get_today(user, day))


@mcp.tool()
async def get_timeline(day: date | None = None) -> Timeline:
    """Return the authenticated user's timeline for one local calendar date."""
    return await _run(AgentScope.TODAY_READ, lambda service, user: service.get_timeline(user, day))


@mcp.tool()
async def get_fitness_summary(request: DateRange) -> Summary:
    """Summarize synced fitness data over a date range."""
    return await _run(
        AgentScope.FITNESS_READ,
        lambda service, user: service.get_fitness_summary(user, request),
    )


@mcp.tool()
async def list_exercises(request: RecordQuery) -> RecordPage:
    """List paginated exercise records over a date range."""
    return await _run(
        AgentScope.FITNESS_READ, lambda service, user: service.list_exercises(user, request)
    )


@mcp.tool()
async def get_exercise(record_id: UUID) -> HealthRecord:
    """Return one exercise belonging to the authenticated user."""
    return await _run(
        AgentScope.FITNESS_READ, lambda service, user: service.get_exercise(user, record_id)
    )


@mcp.tool()
async def get_activity_trend(request: TrendQuery) -> Trend:
    """Return a fitness data-type trend over a date range."""
    return await _run(
        AgentScope.FITNESS_READ,
        lambda service, user: service.get_activity_trend(user, request),
    )


@mcp.tool()
async def get_heart_rate_zones(request: DateRange) -> Summary:
    """Summarize synced heart-rate-zone records over a date range."""
    return await _run(
        AgentScope.FITNESS_READ,
        lambda service, user: service.get_heart_rate_zones(user, request),
    )


@mcp.tool()
async def get_exercise_export(record_id: UUID) -> ExerciseExport:
    """Return a TCX exercise export when Google Health supplied one."""
    return await _run(
        AgentScope.FITNESS_READ,
        lambda service, user: service.get_exercise_export(user, record_id),
    )


@mcp.tool()
async def get_sleep_summary(request: DateRange) -> Summary:
    """Summarize synced sleep data without inventing an official score."""
    return await _run(
        AgentScope.SLEEP_READ,
        lambda service, user: service.get_sleep_summary(user, request),
    )


@mcp.tool()
async def list_sleep_sessions(request: RecordQuery) -> RecordPage:
    """List paginated sleep sessions over a date range."""
    return await _run(
        AgentScope.SLEEP_READ,
        lambda service, user: service.list_sleep_sessions(user, request),
    )


@mcp.tool()
async def get_sleep_session(record_id: UUID) -> HealthRecord:
    """Return one sleep session belonging to the authenticated user."""
    return await _run(
        AgentScope.SLEEP_READ,
        lambda service, user: service.get_sleep_session(user, record_id),
    )


@mcp.tool()
async def get_sleep_trend(request: DateRange) -> Trend:
    """Return sleep record trends over a date range."""
    return await _run(
        AgentScope.SLEEP_READ,
        lambda service, user: service.get_sleep_trend(user, request),
    )


@mcp.tool()
async def get_health_summary(request: DateRange) -> Summary:
    """Summarize non-sensitive health measurements over a date range."""
    return await _run(
        AgentScope.HEALTH_READ,
        lambda service, user: service.get_health_summary(user, request),
    )


@mcp.tool()
async def get_measurement_latest(data_type: str) -> HealthRecord:
    """Return the latest synced record for a non-sensitive measurement type."""
    return await _run(
        AgentScope.HEALTH_READ,
        lambda service, user: service.get_measurement_latest(user, data_type),
    )


@mcp.tool()
async def get_measurement_trend(request: TrendQuery) -> Trend:
    """Return a non-sensitive health measurement trend."""
    return await _run(
        AgentScope.HEALTH_READ,
        lambda service, user: service.get_measurement_trend(user, request),
    )


@mcp.tool()
async def query_health_data(request: RecordQuery) -> RecordPage:
    """Query synced types allowed by the token's category and sensitive-data scopes."""
    principal = _current_principal()
    _require_query_scopes(principal, request.data_types)
    async with SessionFactory() as db:
        return await AgentService(db, get_settings()).query_health_data(principal.user_id, request)


@mcp.tool()
async def list_irregular_rhythm_notifications(request: RecordQuery) -> RecordPage:
    """List irregular-rhythm notifications with the explicit IRN scope."""
    return await _run(
        AgentScope.IRN_READ,
        lambda service, user: service.list_irregular_rhythm_notifications(user, request),
    )


@mcp.tool()
async def list_electrocardiograms(request: RecordQuery) -> RecordPage:
    """List electrocardiograms with the explicit ECG scope."""
    return await _run(
        AgentScope.ECG_READ,
        lambda service, user: service.list_electrocardiograms(user, request),
    )


@mcp.tool()
async def get_electrocardiogram(record_id: UUID) -> HealthRecord:
    """Return one electrocardiogram belonging to the authenticated user."""
    return await _run(
        AgentScope.ECG_READ,
        lambda service, user: service.get_electrocardiogram(user, record_id),
    )


@mcp.tool()
async def get_nutrition_summary(request: DateRange) -> Summary:
    """Summarize synced nutrition data over a date range."""
    return await _run(
        AgentScope.NUTRITION_READ,
        lambda service, user: service.get_nutrition_summary(user, request),
    )


@mcp.tool()
async def list_nutrition_logs(request: RecordQuery) -> RecordPage:
    """List paginated nutrition logs over a date range."""
    return await _run(
        AgentScope.NUTRITION_READ,
        lambda service, user: service.list_nutrition_logs(user, request),
    )


@mcp.tool()
async def list_hydration_logs(request: RecordQuery) -> RecordPage:
    """List paginated hydration logs over a date range."""
    return await _run(
        AgentScope.NUTRITION_READ,
        lambda service, user: service.list_hydration_logs(user, request),
    )


@mcp.tool()
async def get_body_measurements(request: RecordQuery) -> RecordPage:
    """List body-fat, height, and weight records over a date range."""
    return await _run(
        AgentScope.HEALTH_READ,
        lambda service, user: service.get_body_measurements(user, request),
    )


@mcp.tool()
async def get_sync_status() -> SyncStatus:
    """Return synchronization status for all Google Health data types."""
    return await _run(AgentScope.SYNC_READ, lambda service, user: service.get_sync_status(user))


@mcp.tool()
async def get_data_type_sync_status(data_type: str) -> SyncItem:
    """Return synchronization status for one Google Health data type."""
    return await _run(
        AgentScope.SYNC_READ,
        lambda service, user: service.get_data_type_sync_status(user, data_type),
    )


@mcp.tool()
async def trigger_sync(command: SyncCommand) -> SyncQueued:
    """Queue a bounded Google Health synchronization for the authenticated user."""
    return await _run(
        AgentScope.SYNC_WRITE, lambda service, user: service.trigger_sync(user, command)
    )


class BearerAuthMiddleware:
    """Authenticate MCP requests and bind one immutable per-user principal."""

    def __init__(self, application: ASGIApp) -> None:
        self.application = application

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        public_paths = {
            "/healthz",
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-protected-resource/mcp",
            "/oauth/authorize",
            "/oauth/register",
            "/oauth/revoke",
            "/oauth/token",
        }
        if scope["type"] != "http" or scope.get("path") in public_paths:
            await self.application(scope, receive, send)
            return
        raw_token = _bearer_token(scope)
        if raw_token is None:
            await _unauthorized(scope, receive, send)
            return
        try:
            async with SessionFactory() as db:
                principal = await AgentOAuthClientService(db).authenticate_access_token(
                    raw_token,
                    expected_resource=_expected_resource(),
                )
        except AuthenticationError:
            await _unauthorized(scope, receive, send)
            return
        context_token: Token[AgentPrincipal | None] = _principal.set(principal)
        try:
            await self.application(scope, receive, send)
        finally:
            _principal.reset(context_token)


def _bearer_token(scope: Scope) -> str | None:
    headers = scope.get("headers", [])
    values: list[str] = [
        value.decode("latin-1") for name, value in headers if name.lower() == b"authorization"
    ]
    if len(values) != 1:
        return None
    scheme, separator, token = values[0].partition(" ")
    if not separator or scheme.lower() != "bearer" or not token or token.strip() != token:
        return None
    return token


async def _unauthorized(
    scope: Scope,
    receive: Receive,
    send: Send,
) -> None:
    resource = urlsplit(get_settings().mcp_public_url)
    resource_metadata = (
        f"{resource.scheme}://{resource.netloc}/.well-known/oauth-protected-resource"
        f"{resource.path.rstrip('/')}"
    )
    response = JSONResponse(
        {"detail": "Invalid or missing OAuth access token"},
        status_code=401,
        headers={
            "WWW-Authenticate": (
                f'Bearer error="invalid_token", resource_metadata="{resource_metadata}"'
            )
        },
    )
    await response(scope, receive, send)


app = BearerAuthMiddleware(mcp.streamable_http_app())
