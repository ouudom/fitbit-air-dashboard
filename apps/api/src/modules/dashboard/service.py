import json
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.modules.timeline.service import TimelineService


class DashboardService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def get(self, user_id: int, day: date) -> dict[str, object]:
        return {
            "date": day.isoformat(),
            "timezone": self.settings.app_timezone,
            "metrics": await self._metrics(day),
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
                    user_id, day, self.settings.timezone
                )
            ],
            "sync": await self._sync(),
        }

    async def _metrics(self, day: date) -> list[dict[str, object]]:
        steps = await self.db.scalar(
            text("SELECT value FROM daily_metrics WHERE date=:date AND metric='steps'"),
            {"date": day.isoformat()},
        )
        sleep_row = (
            (
                await self.db.execute(
                    text(
                        "SELECT payload, updated_at FROM health_records "
                        "WHERE data_type='sleep' AND date=:date ORDER BY updated_at DESC LIMIT 1"
                    ),
                    {"date": day.isoformat()},
                )
            )
            .mappings()
            .first()
        )
        sleep_minutes = None
        sleep_updated = None
        if sleep_row:
            payload = (
                sleep_row["payload"]
                if isinstance(sleep_row["payload"], dict)
                else json.loads(sleep_row["payload"])
            )
            sleep = payload.get("sleep", payload)
            sleep_minutes = sleep.get("summary", {}).get("minutesAsleep")
            sleep_updated = sleep_row["updated_at"]
        return [
            _metric("Steps", float(steps) if steps is not None else None, "steps", day, None),
            _metric(
                "Sleep",
                round(float(sleep_minutes) / 60, 1) if sleep_minutes is not None else None,
                "h",
                day,
                sleep_updated,
            ),
        ]

    async def _sync(self) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT data_type, status, last_synced_at, record_count, error "
                    "FROM sync_state ORDER BY data_type"
                )
            )
        ).mappings()
        return [
            {
                "dataType": row["data_type"],
                "status": row["status"],
                "lastSyncedAt": _millis_iso(row["last_synced_at"]),
                "recordCount": row["record_count"],
                "error": row["error"],
            }
            for row in rows
        ]


def _metric(
    label: str, value: float | None, unit: str, day: date, updated_at: int | None
) -> dict[str, object]:
    freshness = "unknown"
    if updated_at:
        age = datetime.now(UTC).timestamp() - updated_at / 1000
        freshness = "stale" if age > 24 * 3600 else "fresh"
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


def _millis_iso(value: int | None) -> str | None:
    return datetime.fromtimestamp(value / 1000, UTC).isoformat() if value else None
