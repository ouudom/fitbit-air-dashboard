import asyncio
from uuid import UUID

from celery import Celery

from src.core.config import get_settings
from src.core.database import SessionFactory
from src.modules.google_health.models import GoogleHealthConnection, SyncJob
from src.modules.google_health.sync import SyncService
from src.modules.scoring.service import ScoreService

settings = get_settings()
celery_app = Celery("lifestats", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    beat_schedule={
        "sync-google-health-every-15-minutes": {
            "task": "lifestats.sync_all",
            "schedule": 900,
        }
    },
)


@celery_app.task(name="lifestats.sync_job")  # type: ignore[untyped-decorator]
def sync_job(job_id: str) -> None:
    asyncio.run(_run_job(UUID(job_id)))


@celery_app.task(name="lifestats.sync_all")  # type: ignore[untyped-decorator]
def sync_all() -> None:
    asyncio.run(_run_all())


async def _run_job(job_id: UUID) -> None:
    async with SessionFactory() as db:
        job = await db.get(SyncJob, job_id)
        if job is None:
            return
        job.status = "running"
        await db.commit()
        try:
            result = await SyncService(db, settings, job.user_id).run(job.requested_days)
            await ScoreService(db).calculate_recent(settings.timezone, days=job.requested_days)
            job.status = "complete" if not result["errors"] else "failed"
            job.result = result
            job.error = None if job.status == "complete" else "Some data types failed"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
        await db.commit()


async def _run_all() -> None:
    from sqlalchemy import select

    async with SessionFactory() as db:
        user_ids = list((await db.scalars(select(GoogleHealthConnection.user_id))).all())
        for user_id in user_ids:
            job = SyncJob(user_id=user_id, requested_days=3)
            db.add(job)
            await db.commit()
            sync_job.delay(str(job.id))
