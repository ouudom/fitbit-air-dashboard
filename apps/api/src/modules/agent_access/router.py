from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.dependencies import database_session
from src.core.errors import NotFoundError
from src.modules.agent_access.schemas import (
    IssuedMcpTokenResponse,
    McpTokenCreate,
    McpTokenResponse,
)
from src.modules.agent_access.service import McpTokenService
from src.modules.auth.dependencies import Principal, current_principal, require_csrf

router = APIRouter(prefix="/mcp-tokens", tags=["MCP tokens"])


@router.post("", response_model=IssuedMcpTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_token(
    payload: McpTokenCreate,
    response: Response,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> IssuedMcpTokenResponse:
    response.headers["Cache-Control"] = "no-store"
    issued = await McpTokenService(db).create(
        principal.user_id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    split = urlsplit(settings.mcp_public_url)
    query = [*parse_qsl(split.query, keep_blank_values=True), ("token", issued.token)]
    mcp_url = urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))
    return IssuedMcpTokenResponse.model_validate(
        {
            **McpTokenResponse.model_validate(issued.record).model_dump(),
            "token": issued.token,
            "mcp_url": mcp_url,
        }
    )


@router.get("", response_model=list[McpTokenResponse])
async def list_mcp_tokens(
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> list[McpTokenResponse]:
    rows = await McpTokenService(db).list(principal.user_id)
    return [McpTokenResponse.model_validate(row) for row in rows]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mcp_token(
    token_id: UUID,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> None:
    try:
        await McpTokenService(db).revoke(principal.user_id, token_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
