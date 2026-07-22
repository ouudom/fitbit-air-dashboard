from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.errors import NotFoundError
from src.modules.google_health.writes import GoogleHealthLogWriter
from src.modules.habits.models import HabitEntryRecord, HabitRecord
from src.modules.habits.schemas import EntryCreate, EntryUpdate, HabitCreate, HabitUpdate
from src.modules.habits.service import HabitService
from src.modules.identity.dependencies import (
    Principal,
    current_principal,
    database_session,
    require_csrf,
)

router = APIRouter(tags=["habits"])


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
