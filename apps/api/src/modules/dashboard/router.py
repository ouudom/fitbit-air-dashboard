from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.modules.dashboard.schemas import DashboardResponse
from src.modules.dashboard.service import DashboardService
from src.modules.identity.dependencies import (
    Principal,
    current_principal,
    database_session,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    principal: Annotated[Principal, Depends(current_principal)],
    selected_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    day = selected_date or datetime.now(settings.timezone).date()
    return await DashboardService(db, settings).get(principal.user_id, day)
