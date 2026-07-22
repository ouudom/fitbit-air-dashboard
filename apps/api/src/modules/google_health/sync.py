import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.time import utc_now
from src.modules.google_health.client import GoogleHealthClient
from src.modules.google_health.types import SYNC_TYPES


class SyncService:
    def __init__(self, db: AsyncSession, settings: Settings, user_id: int) -> None:
        self.db = db
        self.settings = settings
        self.user_id = user_id

    async def run(
        self, days: int = 30, data_types: tuple[str, ...] = SYNC_TYPES
    ) -> dict[str, object]:
        end = datetime.now(self.settings.timezone).date()
        start = end - timedelta(days=days - 1)
        client = GoogleHealthClient(self.db, self.settings, self.user_id)
        counts: dict[str, int] = {}
        errors: dict[str, str] = {}
        try:
            for data_type in data_types:
                await self._state(data_type, "running")
                try:
                    if data_type in {"steps", "active-minutes"}:
                        points = await client.daily_rollup(data_type, start, end)
                        await self._save_daily_metrics(data_type, points, start, end)
                    else:
                        points = await client.reconcile_points(data_type, start, end)
                        if data_type == "exercise":
                            await self._save_exercises(points, start, end)
                        else:
                            await self._save_health_records(data_type, points, start, end)
                    counts[data_type] = len(points)
                    await self._state(data_type, "complete", len(points))
                except Exception as exc:
                    await self.db.rollback()
                    errors[data_type] = str(exc)
                    await self._state(data_type, "error", error=str(exc))
        finally:
            await client.close()
        await self.db.execute(
            text(
                "INSERT INTO meta (key, value) VALUES ('lastSync', :value) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"value": str(int(utc_now().timestamp() * 1000))},
        )
        await self.db.commit()
        return {"counts": counts, "errors": errors}

    async def _save_daily_metrics(
        self, data_type: str, points: list[dict[str, Any]], start: date, end: date
    ) -> None:
        await self.db.execute(
            text(
                "DELETE FROM daily_metrics WHERE metric=:metric AND date >= :start AND date <= :end"
            ),
            {"metric": data_type, "start": start.isoformat(), "end": end.isoformat()},
        )
        for point in points:
            observed = _point_date(point)
            value = _number(_inner(point))
            if observed and value is not None:
                await self.db.execute(
                    text(
                        "INSERT INTO daily_metrics (date, metric, value, updated_at) "
                        "VALUES (:date, :metric, :value, :updated_at) "
                        "ON CONFLICT (date, metric) DO UPDATE SET value = EXCLUDED.value, "
                        "updated_at = EXCLUDED.updated_at"
                    ),
                    {
                        "date": observed,
                        "metric": data_type,
                        "value": value,
                        "updated_at": int(utc_now().timestamp() * 1000),
                    },
                )
        await self.db.commit()

    async def _save_health_records(
        self, data_type: str, points: list[dict[str, Any]], start: date, end: date
    ) -> None:
        fetched_ids = [f"{data_type}:{_point_name(point)}" for point in points]
        await self.db.execute(
            text(
                "DELETE FROM health_records WHERE data_type=:type "
                "AND date >= :start AND date <= :end "
                "AND id != ALL(CAST(:ids AS text[]))"
            ),
            {
                "type": data_type,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "ids": fetched_ids,
            },
        )
        for point in points:
            inner = _inner(point)
            record_start = _first(
                inner, "interval.startTime", "sampleTime.physicalTime", "startTime"
            )
            record_end = _first(inner, "interval.endTime", "endTime")
            observed = _point_date(point)
            name = _point_name(point)
            await self.db.execute(
                text(
                    "INSERT INTO health_records "
                    "(id, data_type, start_time, end_time, date, numeric_value, "
                    "payload, updated_at) "
                    "VALUES (:id, :type, :start, :end, :date, :value, "
                    "CAST(:payload AS jsonb), :updated) "
                    "ON CONFLICT (id) DO UPDATE SET data_type = EXCLUDED.data_type, "
                    "start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time, "
                    "date = EXCLUDED.date, numeric_value = EXCLUDED.numeric_value, "
                    "payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at"
                ),
                {
                    "id": f"{data_type}:{name}",
                    "type": data_type,
                    "start": record_start,
                    "end": record_end,
                    "date": observed,
                    "value": _number(inner),
                    "payload": json.dumps(point),
                    "updated": int(utc_now().timestamp() * 1000),
                },
            )
        await self.db.commit()

    async def _save_exercises(self, points: list[dict[str, Any]], start: date, end: date) -> None:
        fetched_ids = [_point_name(point).rsplit("/", 1)[-1] for point in points]
        await self.db.execute(
            text(
                "DELETE FROM exercises WHERE LEFT(start_time, 10) >= :start "
                "AND LEFT(start_time, 10) <= :end "
                "AND id != ALL(CAST(:ids AS text[]))"
            ),
            {"start": start.isoformat(), "end": end.isoformat(), "ids": fetched_ids},
        )
        for point in points:
            exercise = point.get("exercise", {})
            metrics = exercise.get("metricsSummary", {})
            name = _point_name(point)
            await self.db.execute(
                text(
                    "INSERT INTO exercises "
                    "(id, type, display_name, start_time, duration_s, calories, distance_mm, "
                    "steps, avg_hr, raw, updated_at) VALUES "
                    "(:id, :type, :display, :start, :duration, :calories, :distance, :steps, :hr, "
                    "CAST(:raw AS jsonb), :updated) ON CONFLICT (id) DO UPDATE SET "
                    "type=EXCLUDED.type, display_name=EXCLUDED.display_name, "
                    "start_time=EXCLUDED.start_time, duration_s=EXCLUDED.duration_s, "
                    "calories=EXCLUDED.calories, distance_mm=EXCLUDED.distance_mm, "
                    "steps=EXCLUDED.steps, avg_hr=EXCLUDED.avg_hr, raw=EXCLUDED.raw, "
                    "updated_at=EXCLUDED.updated_at"
                ),
                {
                    "id": name.rsplit("/", 1)[-1],
                    "type": exercise.get("exerciseType"),
                    "display": exercise.get("displayName"),
                    "start": _first(exercise, "interval.startTime"),
                    "duration": _duration(exercise.get("activeDuration")),
                    "calories": _number(metrics.get("caloriesKcal")),
                    "distance": _number(
                        metrics.get("distanceMillimeters", metrics.get("distanceMillimiters"))
                    ),
                    "steps": _integer(metrics.get("steps")),
                    "hr": _integer(metrics.get("averageHeartRateBeatsPerMinute")),
                    "raw": json.dumps(point),
                    "updated": int(utc_now().timestamp() * 1000),
                },
            )
        await self.db.commit()

    async def _state(
        self, data_type: str, status: str, count: int = 0, error: str | None = None
    ) -> None:
        now = int(utc_now().timestamp() * 1000)
        await self.db.execute(
            text(
                "INSERT INTO sync_state "
                "(data_type, last_synced_at, status, record_count, error, updated_at) "
                "VALUES (:type, :last, :status, :count, :error, :updated) "
                "ON CONFLICT (data_type) DO UPDATE SET "
                "last_synced_at = CASE WHEN EXCLUDED.status = 'complete' "
                "THEN EXCLUDED.last_synced_at ELSE sync_state.last_synced_at END, "
                "status=EXCLUDED.status, record_count=EXCLUDED.record_count, "
                "error=EXCLUDED.error, updated_at=EXCLUDED.updated_at"
            ),
            {
                "type": data_type,
                "last": now if status == "complete" else None,
                "status": status,
                "count": count,
                "error": error,
                "updated": now,
            },
        )
        await self.db.commit()


def _inner(point: dict[str, Any]) -> dict[str, Any]:
    wrappers = {
        "sleep",
        "exercise",
        "nutritionLog",
        "hydrationLog",
        "weight",
        "dailyHeartRateVariability",
        "dailyRestingHeartRate",
        "heartRate",
    }
    for key, value in point.items():
        if key in wrappers and isinstance(value, dict):
            return value
    return point


def _point_name(point: dict[str, Any]) -> str:
    explicit = point.get("dataPointName") or point.get("name")
    if explicit:
        return str(explicit)
    return json.dumps(point, sort_keys=True, separators=(",", ":"))


def _first(data: dict[str, Any], *paths: str) -> str | None:
    for path in paths:
        value: Any = data
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, str):
            return value
    return None


def _point_date(point: dict[str, Any]) -> str | None:
    inner = _inner(point)
    candidates: list[Any] = [
        inner.get("date"),
        _nested(inner, "civilStartTime.date"),
        _nested(inner, "interval.civilStartTime.date"),
        _nested(inner, "sampleTime.civilTime.date"),
    ]
    for value in candidates:
        if isinstance(value, dict) and all(key in value for key in ("year", "month", "day")):
            return f"{value['year']:04d}-{value['month']:02d}-{value['day']:02d}"
        if isinstance(value, str):
            return value[:10]
    physical = _first(inner, "interval.startTime", "sampleTime.physicalTime", "startTime")
    return physical[:10] if physical else None


def _nested(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, dict):
        preferred = (
            "countSum",
            "sum",
            "total",
            "average",
            "value",
            "bpm",
            "beatsPerMinute",
            "percentage",
            "milliliters",
            "kilograms",
            "averageHeartRateVariabilityMilliseconds",
            "dailyAverageHeartRateVariabilityMilliseconds",
        )
        for key in preferred:
            if key in value and (number := _number(value[key])) is not None:
                return number
        ignored = {
            "date",
            "time",
            "year",
            "month",
            "day",
            "hours",
            "minutes",
            "seconds",
            "nanos",
            "civilStartTime",
            "civilEndTime",
            "sampleTime",
            "interval",
        }
        for key, nested in value.items():
            if key in ignored:
                continue
            if (number := _number(nested)) is not None:
                return number
    return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return round(number) if number is not None else None


def _duration(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return round(value)
    if isinstance(value, str) and value.endswith("s"):
        try:
            return round(float(value[:-1]))
        except ValueError:
            return None
    return None
