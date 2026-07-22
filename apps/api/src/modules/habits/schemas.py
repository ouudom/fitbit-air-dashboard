from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from src.modules.habits.domain import HabitKind, TargetType


class HabitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    kind: HabitKind = HabitKind.LOCAL
    target_type: TargetType = TargetType.BOOLEAN
    target_value: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=24)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))

    @model_validator(mode="after")
    def numeric_requires_target(self) -> "HabitCreate":
        if self.target_type is TargetType.NUMERIC and self.target_value is None:
            raise ValueError("numeric habits require target_value")
        if self.kind is not HabitKind.LOCAL and self.target_type is not TargetType.NUMERIC:
            raise ValueError("Google Health trackers require a numeric target")
        if self.kind is HabitKind.GOOGLE_HYDRATION and not self.unit:
            self.unit = "ml"
        if self.kind is HabitKind.GOOGLE_WEIGHT and not self.unit:
            self.unit = "kg"
        return self


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    target_value: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=24)
    weekdays: list[int] | None = None


class EntryCreate(BaseModel):
    occurred_at: datetime
    value: float = 1
    note: str | None = Field(default=None, max_length=1000)


class EntryUpdate(BaseModel):
    value: float
    note: str | None = Field(default=None, max_length=1000)
