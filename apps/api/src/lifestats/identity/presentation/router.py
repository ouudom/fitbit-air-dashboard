from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.identity.application.service import IdentityService, IssuedSession
from lifestats.shared_kernel.domain.errors import AuthenticationError, ConflictError, NotFoundError
from lifestats.shared_kernel.infrastructure.config import Settings, get_settings
from lifestats.shared_kernel.presentation.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)

router = APIRouter(tags=["identity"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class SetupRequest(Credentials):
    setup_token: str = Field(min_length=1)


class SessionResponse(BaseModel):
    authenticated: bool = True
    user: dict[str, str]
    csrf_token: str | None = None


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


def translate_identity_error(exc: Exception) -> HTTPException:
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
        issued = await IdentityService(db, settings).setup(
            payload.setup_token, payload.email, payload.password
        )
    except (AuthenticationError, ConflictError, NotFoundError) as exc:
        raise translate_identity_error(exc) from exc
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
        issued = await IdentityService(db, settings).login(payload.email, payload.password)
    except AuthenticationError as exc:
        raise translate_identity_error(exc) from exc
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
    await IdentityService(db, settings).logout(token)
    response.delete_cookie("lifestats_session", path="/")
    response.delete_cookie("lifestats_csrf", path="/")


@router.get("/session", response_model=SessionResponse)
async def session(principal: Annotated[Principal, Depends(current_principal)]) -> SessionResponse:
    return SessionResponse(user={"email": principal.email})
