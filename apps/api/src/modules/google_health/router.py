from datetime import timedelta
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.time import utc_now
from src.modules.auth.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)
from src.modules.google_health.models import (
    GhWebhookEvent,
    GoogleHealthConnection,
    GoogleHealthSyncJob,
)
from src.modules.google_health.oauth import OAuthService
from src.modules.google_health.schemas import SyncRequest
from src.modules.google_health.sync import seed_sync_jobs
from src.modules.google_health.tasks import sync_google_health_type
from src.modules.google_health.webhooks import (
    SIGNATURE_HEADER,
    GoogleHealthSignatureVerifier,
    WebhookNotification,
    WebhookSignatureError,
    authorization_matches,
    is_verification_request,
)

router = APIRouter(tags=["google-health"])


@lru_cache
def _signature_verifier(keyset_url: str, ttl_seconds: int) -> GoogleHealthSignatureVerifier:
    return GoogleHealthSignatureVerifier(keyset_url, ttl_seconds=ttl_seconds)


def get_signature_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleHealthSignatureVerifier:
    return _signature_verifier(
        settings.google_health_webhook_keyset_url,
        settings.google_health_webhook_keyset_ttl_seconds,
    )


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
    connection = await db.scalar(
        select(GoogleHealthConnection).where(
            GoogleHealthConnection.user_id == principal.user_id,
            GoogleHealthConnection.status == "active",
        )
    )
    if connection is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Google Health not connected")
    await seed_sync_jobs(db, connection)
    end = utc_now()
    start = end - timedelta(days=payload.days)
    jobs = list(
        (
            await db.scalars(
                select(GoogleHealthSyncJob).where(
                    GoogleHealthSyncJob.connection_id == connection.id,
                    GoogleHealthSyncJob.enabled.is_(True),
                )
            )
        ).all()
    )
    for job in jobs:
        sync_google_health_type.delay(
            str(connection.id),
            job.data_type,
            "manual",
            start.isoformat(),
            end.isoformat(),
        )
    return {"jobId": str(connection.id), "status": "queued"}


@router.get("/sync/{job_id}")
async def sync_status(
    job_id: UUID,
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    connection = await db.scalar(
        select(GoogleHealthConnection).where(
            GoogleHealthConnection.id == job_id,
            GoogleHealthConnection.user_id == principal.user_id,
        )
    )
    if connection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sync job not found")
    jobs = list(
        (
            await db.scalars(
                select(GoogleHealthSyncJob)
                .where(GoogleHealthSyncJob.connection_id == connection.id)
                .order_by(GoogleHealthSyncJob.priority, GoogleHealthSyncJob.data_type)
            )
        ).all()
    )
    statuses = [
        {
            "dataType": job.data_type,
            "fetchMethod": job.fetch_method,
            "status": job.status,
            "recordCount": job.record_count,
            "error": job.error,
            "lastSucceededAt": (
                job.last_succeeded_at.isoformat() if job.last_succeeded_at else None
            ),
        }
        for job in jobs
    ]
    overall = (
        "failed"
        if any(job.status == "failed" for job in jobs)
        else "running"
        if any(job.status in {"queued", "running"} for job in jobs)
        else "completed"
    )
    return {
        "jobId": str(connection.id),
        "status": overall,
        "result": statuses,
        "error": None,
        "updatedAt": max(
            (job.updated_at for job in jobs), default=connection.updated_at
        ).isoformat(),
    }


@router.post("/webhooks/google-health")
async def google_health_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(database_session)],
    verifier: Annotated[GoogleHealthSignatureVerifier, Depends(get_signature_verifier)],
    authorization: Annotated[str | None, Header()] = None,
    google_health_api_signature: Annotated[str | None, Header(alias=SIGNATURE_HEADER)] = None,
) -> Response:
    if not settings.google_health_webhook_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    raw_body = await request.body()
    authorized = authorization_matches(authorization, settings.google_health_webhook_auth_secret)
    if is_verification_request(raw_body):
        if not authorized:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        return Response(status_code=status.HTTP_200_OK)

    if not authorized:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if not google_health_api_signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing webhook signature")
    try:
        await verifier.verify(raw_body, google_health_api_signature)
        notification = WebhookNotification.parse(raw_body)
    except WebhookSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    connection_id = await db.scalar(
        select(GoogleHealthConnection.id).where(
            GoogleHealthConnection.provider_user_id == notification.provider_user_id
        )
    )
    interval_start, interval_end = notification.physical_interval
    civil_start, civil_end = notification.civil_interval
    statement = (
        insert(GhWebhookEvent)
        .values(
            connection_id=connection_id,
            provider_user_id=notification.provider_user_id,
            provider_subscription_name=notification.subscription_name,
            data_type_ids=[notification.data_type],
            operation=notification.operation,
            interval_start=interval_start,
            interval_end=interval_end,
            civil_start_date=civil_start,
            civil_end_date=civil_end,
            event_hash=notification.event_hash,
            raw_payload=notification.raw_payload,
            signature_verified=True,
            status="queued",
        )
        .on_conflict_do_nothing(index_elements=["event_hash"])
        .returning(GhWebhookEvent.id)
    )
    event_id = (await db.execute(statement)).scalar_one_or_none()
    await db.commit()

    if event_id is None:
        duplicate = (
            await db.execute(
                select(GhWebhookEvent.id, GhWebhookEvent.status).where(
                    GhWebhookEvent.event_hash == notification.event_hash
                )
            )
        ).one()
        if duplicate.status in {"queued", "failed"}:
            event_id = duplicate.id
    if event_id is not None:
        from src.modules.google_health.tasks import process_google_health_webhook

        process_google_health_webhook.delay(str(event_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
