from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class HabitKind(StrEnum):
    LOCAL = "local"
    GOOGLE_HYDRATION = "google_hydration"
    GOOGLE_WEIGHT = "google_weight"


class TargetType(StrEnum):
    BOOLEAN = "boolean"
    NUMERIC = "numeric"


@dataclass(frozen=True)
class RemoteLog:
    source_name: str
    occurred_at: datetime
    value: float


class HealthLogWriter(Protocol):
    async def create(self, kind: HabitKind, value: float, occurred_at: datetime) -> RemoteLog: ...

    async def update(
        self, source_name: str, kind: HabitKind, value: float, occurred_at: datetime
    ) -> RemoteLog: ...

    async def delete(self, source_name: str, kind: HabitKind) -> None: ...


def validate_weekdays(days: list[int]) -> list[int]:
    normalized = sorted(set(days))
    if not normalized or any(day < 0 or day > 6 for day in normalized):
        raise ValueError("weekdays must contain values from 0 through 6")
    return normalized
