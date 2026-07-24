from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.capabilities import AppCapabilitiesResponse, app_capabilities
from src.core.config import Settings, get_settings

router = APIRouter(tags=["application"])


@router.get("/capabilities", response_model=AppCapabilitiesResponse)
async def capabilities(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppCapabilitiesResponse:
    return app_capabilities(settings)
