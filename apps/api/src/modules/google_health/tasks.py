import asyncio
from datetime import datetime
from uuid import UUID

from celery import Celery

from src.core.config import get_settings
from src.core.database import SessionFactory
from src.modules.google_health.sync import (
    SyncService,
    claim_due_jobs,
    purge_soft_deleted_records,
)
from src.modules.google_health.webhook_processor import process_webhook_event

settings = get_settings()
celery_app = Celery("lifestats", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    beat_schedule={
        "dispatch-google-health-every-five-minutes": {
            "task": "lifestats.dispatch_google_health",
            "schedule": 300,
        },
        "purge-google-health-soft-deletes-daily": {
            "task": "lifestats.purge_google_health_soft_deleted",
            "schedule": 86_400,
        },
    },
)


@celery_app.task(name="lifestats.sync_google_health_type")  # type: ignore[untyped-decorator]
def sync_google_health_type(
    connection_id: str,
    data_type: str,
    trigger: str = "scheduled",
    range_start: str | None = None,
    range_end: str | None = None,
) -> None:
    asyncio.run(
        _sync_google_health_type(
            UUID(connection_id),
            data_type,
            trigger,
            _parse_datetime(range_start),
            _parse_datetime(range_end),
        )
    )


@celery_app.task(name="lifestats.dispatch_google_health")  # type: ignore[untyped-decorator]
def dispatch_google_health() -> None:
    asyncio.run(_dispatch_google_health())


@celery_app.task(name="lifestats.purge_google_health_soft_deleted")  # type: ignore[untyped-decorator]
def purge_google_health_soft_deleted() -> None:
    asyncio.run(_purge_google_health_soft_deleted())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lifestats.process_google_health_webhook",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=7,
)
def process_google_health_webhook(event_id: str) -> None:
    asyncio.run(_process_google_health_webhook(UUID(event_id)))


async def _sync_google_health_type(
    connection_id: UUID,
    data_type: str,
    trigger: str,
    range_start: datetime | None,
    range_end: datetime | None,
) -> None:
    if trigger not in {"scheduled", "manual", "webhook"}:
        raise ValueError("Unknown Google Health sync trigger")
    async with SessionFactory() as db:
        await SyncService(db, settings, connection_id).sync_type(
            data_type,
            trigger=trigger,
            requested_start=range_start,
            requested_end=range_end,
        )


async def _dispatch_google_health() -> None:
    async with SessionFactory() as db:
        jobs = await claim_due_jobs(db)
    for connection_id, data_type in jobs:
        sync_google_health_type.delay(str(connection_id), data_type, "scheduled", None, None)


async def _process_google_health_webhook(event_id: UUID) -> None:
    async with SessionFactory() as db:
        await process_webhook_event(db, event_id)


async def _purge_google_health_soft_deleted() -> None:
    async with SessionFactory() as db:
        await purge_soft_deleted_records(db)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Sync range timestamps must include a UTC offset")
    return parsed
