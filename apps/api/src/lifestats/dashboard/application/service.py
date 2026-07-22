import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.habits.application.service import HabitService
from lifestats.scoring.domain.model import MODEL_VERSION
from lifestats.shared_kernel.infrastructure.config import Settings
from lifestats.timeline.application.service import TimelineService


class DashboardService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def get(self, user_id: int, day: date) -> dict[str, object]:
        habit_service = HabitService(self.db)
        await habit_service.import_legacy(user_id)
        habits = await habit_service.scheduled(user_id, day)
        entries = await habit_service.entries_for_day(user_id, day, self.settings.timezone)
        by_habit: dict[str, float] = {}
        for entry in entries:
            key = str(entry.habit_id)
            by_habit[key] = by_habit.get(key, 0) + entry.value
        return {
            "date": day.isoformat(),
            "timezone": self.settings.app_timezone,
            "metrics": await self._metrics(day),
            "scores": await self._scores(day),
            "habits": [
                {
                    "id": str(habit.id),
                    "title": habit.title,
                    "kind": habit.kind,
                    "targetType": habit.target_type,
                    "targetValue": habit.target_value,
                    "unit": habit.unit,
                    "progress": by_habit.get(str(habit.id), 0),
                    "complete": (by_habit.get(str(habit.id), 0) >= (habit.target_value or 1)),
                }
                for habit in habits
            ],
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

    async def _scores(self, day: date) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT score_type, value, state, explanation FROM daily_scores "
                    "WHERE date=:date AND model_version=:version"
                ),
                {"date": day.isoformat(), "version": MODEL_VERSION},
            )
        ).mappings()
        found = {row["score_type"]: row for row in rows}
        result: list[dict[str, object]] = []
        for score_type in ("readiness", "stress", "energy"):
            row = found.get(score_type)
            explanation: dict[str, Any] = {}
            if row and row["explanation"]:
                explanation = (
                    row["explanation"]
                    if isinstance(row["explanation"], dict)
                    else json.loads(row["explanation"])
                )
            result.append(
                {
                    "key": score_type,
                    "label": f"LifeStats {score_type.title()}",
                    "value": row["value"] if row else None,
                    "status": row["state"] if row else "unavailable",
                    "modelVersion": MODEL_VERSION,
                    "components": explanation.get("components", {}),
                    "missingInputs": explanation.get("missingInputs", ["baseline"]),
                    "explanation": explanation.get(
                        "summary", "Sync enough personal history to calculate this estimate."
                    ),
                    "disclaimer": "Wellness estimate, not medical advice.",
                }
            )
        return result

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
