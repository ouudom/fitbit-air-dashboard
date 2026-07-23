from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.modules.auth.models import User
from src.modules.google_health.models import (
    GoogleHealthConnection,
    GoogleHealthRecord,
    GoogleHealthSyncJob,
)
from src.modules.google_health.normalization import extract_number
from src.modules.timeline.service import TimelineService


class DashboardService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def get(self, user_id: int, day: date | None) -> dict[str, object]:
        timezone_name = await self.db.scalar(select(User.timezone).where(User.id == user_id))
        timezone = ZoneInfo(timezone_name or self.settings.app_timezone)
        selected_day = day or datetime.now(timezone).date()
        return {
            "date": selected_day.isoformat(),
            "timezone": timezone.key,
            "metrics": await self._metrics(user_id, selected_day, timezone),
            "timeline": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "title": item.title,
                    "occurredAt": item.occurred_at.isoformat(),
                    "source": item.source,
                    "detail": item.detail,
                    "freshness": item.freshness,
                }
                for item in await TimelineService(self.db).for_day(
                    user_id,
                    selected_day,
                    timezone,
                )
            ],
            "sync": await self._sync(user_id),
        }

    async def _metrics(
        self, user_id: int, day: date, timezone: ZoneInfo
    ) -> list[dict[str, object]]:
        records = await self._records_for_day(
            user_id,
            day,
            timezone,
            ("steps", "sleep"),
        )
        step_records = [record for record in records if record.data_type == "steps"]
        steps = sum(
            value
            for record in step_records
            if (value := extract_number(record.raw_payload)) is not None
        )
        sleep_row = next(
            (
                record
                for record in sorted(
                    (item for item in records if item.data_type == "sleep"),
                    key=lambda item: item.last_synced_at,
                    reverse=True,
                )
            ),
            None,
        )
        sleep_minutes = None
        sleep_updated = None
        if sleep_row:
            payload = sleep_row.raw_payload
            sleep = payload.get("sleep", payload)
            if isinstance(sleep, dict):
                summary = sleep.get("summary", {})
                if isinstance(summary, dict):
                    sleep_minutes = summary.get("minutesAsleep")
            sleep_updated = sleep_row.last_synced_at
        return [
            _metric(
                "Steps",
                steps if step_records else None,
                "steps",
                day,
                max(
                    (record.last_synced_at for record in step_records),
                    default=None,
                ),
            ),
            _metric(
                "Sleep",
                round(float(sleep_minutes) / 60, 1) if sleep_minutes is not None else None,
                "h",
                day,
                sleep_updated,
            ),
        ]

    async def _records_for_day(
        self,
        user_id: int,
        day: date,
        timezone: ZoneInfo,
        data_types: tuple[str, ...],
    ) -> list[GoogleHealthRecord]:
        local_start = datetime.combine(day, time.min, timezone)
        utc_start = local_start.astimezone(UTC)
        utc_end = (local_start + timedelta(days=1)).astimezone(UTC)
        query = (
            select(GoogleHealthRecord)
            .join(
                GoogleHealthConnection,
                GoogleHealthConnection.id == GoogleHealthRecord.connection_id,
            )
            .where(
                GoogleHealthConnection.user_id == user_id,
                GoogleHealthRecord.data_type.in_(data_types),
                GoogleHealthRecord.deleted_at.is_(None),
                or_(
                    GoogleHealthRecord.record_date == day,
                    (
                        (GoogleHealthRecord.started_at >= utc_start)
                        & (GoogleHealthRecord.started_at < utc_end)
                    ),
                ),
            )
        )
        return list((await self.db.scalars(query)).all())

    async def _sync(self, user_id: int) -> list[dict[str, object]]:
        query = (
            select(GoogleHealthSyncJob)
            .join(
                GoogleHealthConnection,
                GoogleHealthConnection.id == GoogleHealthSyncJob.connection_id,
            )
            .where(GoogleHealthConnection.user_id == user_id)
            .order_by(GoogleHealthSyncJob.data_type)
        )
        rows = (await self.db.scalars(query)).all()
        return [
            {
                "dataType": row.data_type,
                "status": row.status,
                "lastSyncedAt": (
                    row.last_succeeded_at.isoformat() if row.last_succeeded_at else None
                ),
                "recordCount": row.record_count,
                "error": row.error,
            }
            for row in rows
        ]


def _metric(
    label: str,
    value: float | None,
    unit: str,
    day: date,
    updated_at: datetime | None,
) -> dict[str, object]:
    freshness = "unknown"
    if updated_at:
        age = datetime.now(UTC) - updated_at.astimezone(UTC)
        freshness = "stale" if age > timedelta(days=1) else "fresh"
    return {
        "key": label.lower(),
        "label": label,
        "value": value,
        "unit": unit,
        "source": "Google Health",
        "observedAt": day.isoformat(),
        "freshness": freshness,
        "availability": "available" if value is not None else "not-synced",
    }
