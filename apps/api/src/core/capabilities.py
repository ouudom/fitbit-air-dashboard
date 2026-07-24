from typing import Annotated

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from src.core.config import Settings, get_settings


class AppCapabilitiesResponse(BaseModel):
    agentAccessEnabled: bool


def app_capabilities(settings: Settings) -> AppCapabilitiesResponse:
    return AppCapabilitiesResponse(agentAccessEnabled=settings.agent_access_enabled)


def require_agent_access(
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not settings.agent_access_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
