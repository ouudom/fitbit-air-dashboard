import json
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.timeline.domain.models import TimelineItem


class TimelineService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_day(self, user_id: int, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        items = await self._health(day, timezone)
        items.extend(await self._workouts(day, timezone))
        items.extend(await self._habits(user_id, day, timezone))
        unique = {item.id: item for item in items}
        return sorted(unique.values(), key=lambda item: item.occurred_at, reverse=True)

    async def _health(self, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT id, data_type, start_time, date, payload, updated_at "
                    "FROM health_records "
                    "WHERE date=:date AND data_type IN "
                    "('sleep','nutrition-log','hydration-log','weight')"
                ),
                {"date": day.isoformat()},
            )
        ).mappings()
        result: list[TimelineItem] = []
        for row in rows:
            payload = (
                row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
            )
            occurred = _parse_time(row["start_time"], day, timezone)
            data_type = row["data_type"]
            title, detail = _health_label(data_type, payload)
            result.append(
                TimelineItem(
                    id=f"google:{row['id']}",
                    kind=data_type,
                    title=title,
                    occurred_at=occurred,
                    source="Google Health",
                    detail=detail,
                    freshness=_freshness(row["updated_at"]),
                )
            )
        return result

    async def _workouts(self, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT id, display_name, type, start_time, duration_s, updated_at "
                    "FROM exercises "
                    "WHERE LEFT(start_time, 10)=:date"
                ),
                {"date": day.isoformat()},
            )
        ).mappings()
        return [
            TimelineItem(
                id=f"google:exercise:{row['id']}",
                kind="exercise",
                title=row["display_name"] or row["type"] or "Workout",
                occurred_at=_parse_time(row["start_time"], day, timezone),
                source="Google Health",
                detail=f"{round(row['duration_s'] / 60)} min" if row["duration_s"] else None,
                freshness=_freshness(row["updated_at"]),
            )
            for row in rows
        ]

    async def _habits(self, user_id: int, day: date, timezone: ZoneInfo) -> list[TimelineItem]:
        start = datetime.combine(day, time.min, timezone)
        end = datetime.combine(day, time.max, timezone)
        rows = (
            await self.db.execute(
                text(
                    "SELECT e.id, e.occurred_at, e.value, e.note, e.source, h.title, h.unit "
                    "FROM habit_entries_v1 e JOIN habits_v1 h ON h.id=e.habit_id "
                    "WHERE e.user_id=:user_id AND e.source <> 'google-health' "
                    "AND e.occurred_at BETWEEN :start AND :end"
                ),
                {"user_id": user_id, "start": start, "end": end},
            )
        ).mappings()
        return [
            TimelineItem(
                id=f"habit:{row['id']}",
                kind="habit",
                title=row["title"],
                occurred_at=row["occurred_at"],
                source="Google Health" if row["source"] == "google-health" else "LifeStats",
                detail=(f"{row['value']:g} {row['unit'] or ''}".strip()),
            )
            for row in rows
        ]


def _parse_time(value: str | None, day: date, timezone: ZoneInfo) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone)
    return datetime.combine(day, time.min, timezone)


def _freshness(updated_at: int | None) -> str:
    if not updated_at:
        return "unknown"
    age = datetime.now(UTC).timestamp() - updated_at / 1000
    return "stale" if age > 24 * 3600 else "fresh"


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
