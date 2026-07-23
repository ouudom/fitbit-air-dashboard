from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.google_health.models import GoogleHealthConnection, GoogleHealthRecord
from src.modules.timeline.domain import TimelineItem


class TimelineService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_day(self, user_id: int, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        items = await self._health(user_id, day, timezone)
        items.extend(await self._workouts(user_id, day, timezone))
        unique = {item.id: item for item in items}
        return sorted(unique.values(), key=lambda item: item.occurred_at, reverse=True)

    async def _health(self, user_id: int, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        rows = await self._records_for_day(
            user_id,
            day,
            timezone,
            ("sleep", "nutrition-log", "hydration-log", "weight"),
        )
        result: list[TimelineItem] = []
        for row in rows:
            occurred = row.started_at or datetime.combine(day, time.min, timezone)
            title, detail = _health_label(row.data_type, row.raw_payload)
            result.append(
                TimelineItem(
                    id=f"google:{row.id}",
                    kind=row.data_type,
                    title=title,
                    occurred_at=occurred,
                    source="Google Health",
                    detail=detail,
                    freshness=_freshness(row.last_synced_at),
                )
            )
        return result

    async def _workouts(self, user_id: int, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        rows = await self._records_for_day(user_id, day, timezone, ("exercise",))
        result: list[TimelineItem] = []
        for row in rows:
            exercise = row.raw_payload.get("exercise", row.raw_payload)
            exercise = exercise if isinstance(exercise, dict) else {}
            duration = _duration_seconds(exercise.get("activeDuration"))
            result.append(
                TimelineItem(
                    id=f"google:exercise:{row.id}",
                    kind="exercise",
                    title=str(
                        exercise.get("displayName") or exercise.get("exerciseType") or "Workout"
                    ),
                    occurred_at=row.started_at or datetime.combine(day, time.min, timezone),
                    source="Google Health",
                    detail=f"{round(duration / 60)} min" if duration else None,
                    freshness=_freshness(row.last_synced_at),
                )
            )
        return result

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


def _freshness(updated_at: datetime | None) -> str:
    if not updated_at:
        return "unknown"
    age = datetime.now(UTC) - updated_at.astimezone(UTC)
    return "stale" if age > timedelta(days=1) else "fresh"


def _health_label(data_type: str, payload: dict[str, Any]) -> tuple[str, str | None]:
    inner = payload.get(data_type.replace("-", ""), payload.get(_camel(data_type), payload))
    if data_type == "sleep":
        minutes = inner.get("summary", {}).get("minutesAsleep") if isinstance(inner, dict) else None
        return "Sleep", f"{round(minutes / 60, 1)} h" if isinstance(minutes, (int, float)) else None
    if data_type == "nutrition-log":
        return "Nutrition logged", None
    if data_type == "hydration-log":
        value = _find_number(inner, ("milliliters",))
        return "Water logged", f"{value:g} ml" if value is not None else None
    value = _find_number(inner, ("kilograms",))
    return "Weight logged", f"{value:g} kg" if value is not None else None


def _camel(value: str) -> str:
    head, *tail = value.split("-")
    return head + "".join(part.title() for part in tail)


def _find_number(value: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in keys and isinstance(nested, (int, float)):
                return float(nested)
            if (found := _find_number(nested, keys)) is not None:
                return found
    return None


def _duration_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.endswith("s"):
        try:
            return float(value[:-1])
        except ValueError:
            return None
    return None
