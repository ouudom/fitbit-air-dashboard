from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.errors import AuthenticationError, ConflictError, NotFoundError
from src.modules.auth.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)
from src.modules.auth.schemas import Credentials, SessionResponse, SetupRequest
from src.modules.auth.service import AuthService, IssuedSession

router = APIRouter(tags=["auth"])


def set_session_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    max_age = settings.session_lifetime_hours * 3600
    response.set_cookie(
        "lifestats_session",
        issued.token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        "lifestats_csrf",
        issued.csrf_token,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


def translate_auth_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))


@router.post("/setup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def setup(
    payload: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    try:
        issued = await AuthService(db, settings).setup(
            payload.setup_token, payload.email, payload.password
        )
    except (AuthenticationError, ConflictError, NotFoundError) as exc:
        raise translate_auth_error(exc) from exc
    set_session_cookies(response, issued, settings)
    return SessionResponse(user={"email": issued.user.email}, csrf_token=issued.csrf_token)


@router.post("/auth/login", response_model=SessionResponse)
async def login(
    payload: Credentials,
    response: Response,
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    try:
        issued = await AuthService(db, settings).login(payload.email, payload.password)
    except AuthenticationError as exc:
        raise translate_auth_error(exc) from exc
    set_session_cookies(response, issued, settings)
    return SessionResponse(user={"email": issued.user.email}, csrf_token=issued.csrf_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _: Annotated[Principal, Depends(require_csrf)],
    token: str | None = Cookie(default=None, alias="lifestats_session"),
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> None:
    await AuthService(db, settings).logout(token)
    response.delete_cookie("lifestats_session", path="/")
    response.delete_cookie("lifestats_csrf", path="/")


@router.get("/session", response_model=SessionResponse)
async def session(principal: Annotated[Principal, Depends(current_principal)]) -> SessionResponse:
    return SessionResponse(user={"email": principal.email})
