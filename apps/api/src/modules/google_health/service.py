from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.errors import ConflictError, NotFoundError
from src.core.time import utc_now
from src.modules.google_health.models import (
    GoogleHealthConnection,
    GoogleHealthSyncJob,
)
from src.modules.google_health.oauth import OAuthService
from src.modules.google_health.registry import DATA_TYPE_REGISTRY
from src.modules.google_health.repository import GoogleHealthRepository
from src.modules.google_health.schemas import SyncRequest
from src.modules.google_health.sync import seed_sync_jobs
from src.modules.google_health.tasks import sync_google_health_type


class GoogleHealthService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings
        self.repository = GoogleHealthRepository(db)

    async def integration_status(self, user_id: int) -> dict[str, object]:
        connection = await self.repository.connection_for_user(user_id)
        if connection is None:
            return {
                "connected": False,
                "status": "disconnected",
                "grantedScopes": [],
                "enabledDataTypes": 0,
                "totalDataTypes": len(DATA_TYPE_REGISTRY),
            }
        jobs = await self.repository.jobs_for_connection(connection.id)
        return {
            "connected": connection.status == "active",
            "status": connection.status,
            "grantedScopes": connection.scopes,
            "enabledDataTypes": sum(job.enabled for job in jobs),
            "totalDataTypes": len(DATA_TYPE_REGISTRY),
            "lastVerifiedAt": (
                connection.last_verified_at.isoformat() if connection.last_verified_at else None
            ),
            "tokenExpiresAt": (
                connection.token_expires_at.isoformat() if connection.token_expires_at else None
            ),
        }

    async def disconnect(self, user_id: int) -> dict[str, object]:
        connection = await self.repository.connection_for_user(user_id)
        if connection is None:
            return {"status": "disconnected", "cacheRetained": True}
        if self.settings is None:
            raise RuntimeError("Google Health settings required")
        await OAuthService(self.db, self.settings).revoke_token(connection)
        connection.access_token_ciphertext = ""
        connection.refresh_token_ciphertext = None
        connection.token_expires_at = None
        connection.status = "revoked"
        for job in await self.repository.jobs_for_connection(connection.id):
            job.enabled = False
            job.lease_until = None
            job.next_page_token = None
            job.status = "completed"
            job.error = "connection_disconnected"
        await self.db.commit()
        return {"status": "revoked", "cacheRetained": True}

    async def queue_sync(
        self,
        user_id: int,
        payload: SyncRequest,
        requested_type: str | None = None,
    ) -> list[str]:
        connection = await self.repository.connection_for_user(user_id, active_only=True)
        if connection is None:
            raise ConflictError("Google Health not connected")
        return await self._queue_manual_sync(connection, payload, requested_type)

    async def _queue_manual_sync(
        self,
        connection: GoogleHealthConnection,
        payload: SyncRequest,
        requested_type: str | None = None,
    ) -> list[str]:
        await seed_sync_jobs(self.db, connection)
        requested = [requested_type] if requested_type else payload.data_types
        if requested:
            unknown = sorted(set(requested) - DATA_TYPE_REGISTRY.keys())
            if unknown:
                raise NotFoundError(f"Unsupported Google Health data type: {', '.join(unknown)}")
        jobs = await self.repository.jobs_for_connection(connection.id)
        enabled_by_type = {job.data_type: job for job in jobs if job.enabled}
        selected = requested or list(enabled_by_type)
        unavailable = sorted(set(selected) - enabled_by_type.keys())
        if unavailable:
            raise ConflictError(f"Data type not granted or enabled: {', '.join(unavailable)}")
        if not selected:
            raise ConflictError("No granted Google Health data types")
        range_start, range_end = self._manual_window(payload)
        for data_type in selected:
            sync_google_health_type.delay(
                str(connection.id),
                data_type,
                "manual",
                range_start,
                range_end,
            )
        return selected

    async def sync_jobs(self, user_id: int) -> dict[str, object]:
        connection = await self.repository.connection_for_user(user_id)
        if connection is None:
            raise NotFoundError("Google Health connection not found")
        jobs = await self.repository.jobs_for_connection(connection.id)
        return {
            "connectionId": str(connection.id),
            "status": self._overall_status(jobs),
            "items": [self._job_status(job) for job in jobs],
        }

    async def sync_status(self, user_id: int, data_type: str) -> dict[str, object]:
        if data_type not in DATA_TYPE_REGISTRY:
            raise NotFoundError(f"Unsupported Google Health data type: {data_type}")
        connection = await self.repository.connection_for_user(user_id)
        if connection is None:
            raise NotFoundError("Sync job not found")
        jobs = await self.repository.jobs_for_connection(connection.id)
        job = next((item for item in jobs if item.data_type == data_type), None)
        if job is None:
            raise NotFoundError("Sync job not found")
        return self._job_status(job)

    @staticmethod
    def _manual_window(payload: SyncRequest) -> tuple[str, str]:
        end = payload.end_at or utc_now()
        start = payload.start_at or end - timedelta(days=payload.days)
        return start.isoformat(), end.isoformat()

    @staticmethod
    def _job_status(job: GoogleHealthSyncJob) -> dict[str, object]:
        return {
            "dataType": job.data_type,
            "fetchMethod": job.fetch_method,
            "enabled": job.enabled,
            "status": job.status,
            "recordCount": job.record_count,
            "error": job.error,
            "nextPollAt": job.next_poll_at.isoformat(),
            "lastAttemptedAt": (
                job.last_attempted_at.isoformat() if job.last_attempted_at else None
            ),
            "lastSucceededAt": (
                job.last_succeeded_at.isoformat() if job.last_succeeded_at else None
            ),
            "updatedAt": job.updated_at.isoformat(),
        }

    @staticmethod
    def _overall_status(jobs: list[GoogleHealthSyncJob]) -> str:
        enabled = [job for job in jobs if job.enabled]
        if any(job.status == "failed" for job in enabled):
            return "failed"
        if any(job.status in {"queued", "running"} for job in enabled):
            return "running"
        return "completed"
