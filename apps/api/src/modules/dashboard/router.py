from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.dependencies import database_session
from src.modules.auth.dependencies import (
    Principal,
    current_principal,
)
from src.modules.dashboard.schemas import DashboardResponse, InsightsResponse
from src.modules.dashboard.service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    principal: Annotated[Principal, Depends(current_principal)],
    selected_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return await DashboardService(db, settings).get(principal.user_id, selected_date)


@router.get("/insights", response_model=InsightsResponse)
async def insights(
    principal: Annotated[Principal, Depends(current_principal)],
    start: date = Query(),
    end: date = Query(),
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="date range cannot exceed 366 days")
    return await DashboardService(db, settings).get_insights(principal.user_id, start, end)
