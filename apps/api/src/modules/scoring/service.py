import json
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.time import utc_now
from src.modules.scoring.domain import (
    MODEL_VERSION,
    ScoreResult,
    Signal,
    component,
    weighted_components,
    weighted_score,
)


class ScoreService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_recent(self, timezone: ZoneInfo, days: int = 30) -> None:
        today = utc_now().astimezone(timezone).date()
        for offset in range(max(0, days - 1), -1, -1):
            await self.calculate(today - timedelta(days=offset))
        await self.db.commit()

    async def calculate(self, target: date) -> dict[str, ScoreResult]:
        baseline_start = target - timedelta(days=28)
        sleep = await self._sleep(baseline_start, target)
        hrv = await self._records("daily-heart-rate-variability", baseline_start, target)
        resting_hr = await self._records("daily-resting-heart-rate", baseline_start, target)
        activity = await self._metrics("active-minutes", baseline_start, target)
        prior = target - timedelta(days=1)

        sleep_signal = Signal(sleep.get(target), _history(sleep, target))
        hrv_signal = Signal(hrv.get(target), _history(hrv, target))
        rhr_signal = Signal(resting_hr.get(target), _history(resting_hr, target), inverse=True)
        activity_signal = Signal(activity.get(prior), _history(activity, prior), inverse=True)

        recovery_available = hrv_signal.current is not None or rhr_signal.current is not None
        eligible = sleep_signal.current is not None and recovery_available
        if eligible:
            readiness = weighted_score(
                {
                    "hrv": hrv_signal,
                    "restingHeartRate": rhr_signal,
                    "sleepDuration": sleep_signal,
                    "activityBalance": activity_signal,
                },
                {
                    "hrv": 0.35,
                    "restingHeartRate": 0.25,
                    "sleepDuration": 0.30,
                    "activityBalance": 0.10,
                },
            )
            stress = weighted_score(
                {
                    "hrv": hrv_signal,
                    "restingHeartRate": rhr_signal,
                    "sleepDuration": sleep_signal,
                },
                {"hrv": 0.45, "restingHeartRate": 0.35, "sleepDuration": 0.20},
                invert_result=True,
            )
            energy = weighted_components(
                {
                    "readiness": readiness.value,
                    "sleepDuration": component(sleep_signal),
                    "activityBalance": component(activity_signal),
                },
                {"readiness": 0.45, "sleepDuration": 0.35, "activityBalance": 0.20},
            )
        else:
            missing = [
                name
                for name, present in {
                    "sleepDuration": sleep_signal.current is not None,
                    "recoverySignal": recovery_available,
                }.items()
                if not present
            ]
            unavailable = ScoreResult(None, {}, missing, "unavailable")
            readiness = stress = energy = unavailable

        results = {"readiness": readiness, "stress": stress, "energy": energy}
        inputs = {
            "sleepDuration": sleep_signal.current,
            "hrv": hrv_signal.current,
            "restingHeartRate": rhr_signal.current,
            "previousActivity": activity_signal.current,
        }
        for score_type, result in results.items():
            await self._persist(target, score_type, result, inputs)
        return results

    async def _persist(
        self, target: date, score_type: str, result: ScoreResult, inputs: dict[str, float | None]
    ) -> None:
        explanation = {
            "components": result.components,
            "missingInputs": result.missing,
            "summary": (
                "Calculated from your rolling 28-day baseline."
                if result.value is not None
                else "At least 14 baseline days, sleep, and one recovery signal are required."
            ),
            "disclaimer": "Wellness estimate, not medical advice.",
        }
        await self.db.execute(
            text(
                "INSERT INTO daily_scores "
                "(date, score_type, model_version, value, confidence, state, inputs, "
                "explanation, updated_at) "
                "VALUES (:date, :type, :version, :value, :confidence, :state, "
                "CAST(:inputs AS jsonb), CAST(:explanation AS jsonb), :updated) "
                "ON CONFLICT (date, score_type, model_version) DO UPDATE SET "
                "value=EXCLUDED.value, confidence=EXCLUDED.confidence, state=EXCLUDED.state, "
                "inputs=EXCLUDED.inputs, explanation=EXCLUDED.explanation, "
                "updated_at=EXCLUDED.updated_at"
            ),
            {
                "date": target.isoformat(),
                "type": score_type,
                "version": MODEL_VERSION,
                "value": result.value,
                "confidence": "personal-baseline"
                if result.value is not None
                else "insufficient-data",
                "state": result.status,
                "inputs": json.dumps(inputs),
                "explanation": json.dumps(explanation),
                "updated": int(utc_now().timestamp() * 1000),
            },
        )

    async def _metrics(self, metric: str, start: date, end: date) -> dict[date, float]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT date, value FROM daily_metrics "
                    "WHERE metric=:metric AND date >= :start AND date <= :end AND value IS NOT NULL"
                ),
                {"metric": metric, "start": start.isoformat(), "end": end.isoformat()},
            )
        ).mappings()
        return {date.fromisoformat(row["date"]): float(row["value"]) for row in rows}

    async def _records(self, data_type: str, start: date, end: date) -> dict[date, float]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT date, numeric_value FROM health_records "
                    "WHERE data_type=:type AND date >= :start AND date <= :end "
                    "AND numeric_value IS NOT NULL ORDER BY updated_at"
                ),
                {"type": data_type, "start": start.isoformat(), "end": end.isoformat()},
            )
        ).mappings()
        return {date.fromisoformat(row["date"]): float(row["numeric_value"]) for row in rows}

    async def _sleep(self, start: date, end: date) -> dict[date, float]:
        rows = (
            await self.db.execute(
                text(
                    "SELECT date, payload FROM health_records WHERE data_type='sleep' "
                    "AND date >= :start AND date <= :end ORDER BY updated_at"
                ),
                {"start": start.isoformat(), "end": end.isoformat()},
            )
        ).mappings()
        result: dict[date, float] = {}
        for row in rows:
            payload = (
                row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
            )
            sleep = payload.get("sleep", payload)
            minutes = sleep.get("summary", {}).get("minutesAsleep")
            if row["date"] and isinstance(minutes, (int, float)):
                result[date.fromisoformat(row["date"])] = float(minutes)
        return result


def _history(values: dict[date, float], before: date) -> list[float]:
    return [value for day, value in values.items() if day < before][-28:]
