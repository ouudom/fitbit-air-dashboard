from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.google_health.application.writes import GoogleHealthLogWriter
from lifestats.habits.application.service import HabitService
from lifestats.habits.domain.models import HabitKind, TargetType
from lifestats.habits.infrastructure.models import HabitEntryRecord, HabitRecord
from lifestats.shared_kernel.domain.errors import NotFoundError
from lifestats.shared_kernel.infrastructure.config import get_settings
from lifestats.shared_kernel.presentation.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)

router = APIRouter(tags=["habits"])


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


def habit_json(row: HabitRecord) -> dict[str, object]:
    return {
        "id": str(row.id),
        "title": row.title,
        "kind": row.kind,
        "targetType": row.target_type,
        "targetValue": row.target_value,
        "unit": row.unit,
        "weekdays": row.weekdays,
        "active": row.active,
    }


def entry_json(row: HabitEntryRecord) -> dict[str, object]:
    return {
        "id": str(row.id),
        "habitId": str(row.habit_id),
        "occurredAt": row.occurred_at.isoformat(),
        "value": row.value,
        "note": row.note,
        "source": row.source,
    }


def service(db: AsyncSession, user_id: int) -> HabitService:
    return HabitService(db, GoogleHealthLogWriter(db, get_settings(), user_id))


@router.get("/habits")
async def list_habits(
    principal: Annotated[Principal, Depends(current_principal)],
    db: AsyncSession = Depends(database_session),
) -> list[dict[str, object]]:
    return [
        habit_json(row)
        for row in await service(db, principal.user_id).list_habits(principal.user_id)
    ]


@router.post("/habits", status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    values = payload.model_dump(mode="json")
    return habit_json(await service(db, principal.user_id).create(principal.user_id, values))


@router.patch("/habits/{habit_id}")
async def update_habit(
    habit_id: UUID,
    payload: HabitUpdate,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    try:
        row = await service(db, principal.user_id).update(
            principal.user_id, habit_id, payload.model_dump(exclude_unset=True)
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return habit_json(row)


@router.delete("/habits/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_habit(
    habit_id: UUID,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> None:
    try:
        await service(db, principal.user_id).archive(principal.user_id, habit_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/habits/{habit_id}/entries", status_code=status.HTTP_201_CREATED)
async def create_entry(
    habit_id: UUID,
    payload: EntryCreate,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    try:
        row = await service(db, principal.user_id).create_entry(
            principal.user_id, habit_id, **payload.model_dump()
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return entry_json(row)


@router.patch("/habit-entries/{entry_id}")
async def update_entry(
    entry_id: UUID,
    payload: EntryUpdate,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> dict[str, object]:
    try:
        row = await service(db, principal.user_id).update_entry(
            principal.user_id, entry_id, **payload.model_dump()
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return entry_json(row)


@router.delete("/habit-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: AsyncSession = Depends(database_session),
) -> None:
    try:
        await service(db, principal.user_id).delete_entry(principal.user_id, entry_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
