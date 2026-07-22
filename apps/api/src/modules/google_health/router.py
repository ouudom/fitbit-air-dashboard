from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.modules.google_health.models import SyncJob
from src.modules.google_health.oauth import OAuthService
from src.modules.google_health.schemas import SyncRequest
from src.modules.google_health.tasks import sync_job
from src.modules.identity.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)

router = APIRouter(tags=["google-health"])


@router.get("/integrations/google-health/connect")
async def connect(
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    url = await OAuthService(db, settings).authorization_url(principal.user_id)
    return RedirectResponse(url)


@router.get("/oauth/google-health/callback")
async def callback(
    state: str = Query(min_length=1),
    code: str = Query(min_length=1),
    db: AsyncSession = Depends(database_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    try:
        await OAuthService(db, settings).callback(state, code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return RedirectResponse("/?connected=1", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def queue_sync(
    payload: SyncRequest,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, str]:
    job = SyncJob(user_id=principal.user_id, requested_days=payload.days)
    db.add(job)
    await db.commit()
    sync_job.delay(str(job.id))
    return {"jobId": str(job.id), "status": job.status}


@router.get("/sync/{job_id}")
async def sync_status(
    job_id: UUID,
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    job = await db.get(SyncJob, job_id)
    if job is None or job.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sync job not found")
    return {
        "jobId": str(job.id),
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "updatedAt": job.updated_at.isoformat(),
    }
