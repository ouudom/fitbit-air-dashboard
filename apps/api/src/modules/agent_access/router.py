from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import database_session
from src.core.errors import NotFoundError
from src.modules.agent_access.schemas import (
    AgentTokenCreate,
    AgentTokenResponse,
    IssuedAgentTokenResponse,
)
from src.modules.agent_access.service import AgentTokenService
from src.modules.auth.dependencies import Principal, current_principal, require_csrf

router = APIRouter(prefix="/agent-tokens", tags=["agent tokens"])


@router.post("", response_model=IssuedAgentTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_token(
    payload: AgentTokenCreate,
    response: Response,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> IssuedAgentTokenResponse:
    response.headers["Cache-Control"] = "no-store"
    issued = await AgentTokenService(db).create(
        principal.user_id,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    return IssuedAgentTokenResponse.model_validate(
        {**AgentTokenResponse.model_validate(issued.record).model_dump(), "token": issued.token}
    )


@router.get("", response_model=list[AgentTokenResponse])
async def list_agent_tokens(
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> list[AgentTokenResponse]:
    rows = await AgentTokenService(db).list(principal.user_id)
    return [AgentTokenResponse.model_validate(row) for row in rows]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_token(
    token_id: UUID,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> None:
    try:
        await AgentTokenService(db).revoke(principal.user_id, token_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
