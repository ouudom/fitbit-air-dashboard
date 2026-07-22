from collections.abc import Iterable
from datetime import date, datetime, time
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.habits.domain.models import HabitKind, HealthLogWriter, validate_weekdays
from lifestats.habits.infrastructure.models import HabitEntryRecord, HabitRecord
from lifestats.shared_kernel.domain.errors import NotFoundError


class HabitService:
    def __init__(self, db: AsyncSession, writer: HealthLogWriter | None = None) -> None:
        self.db = db
        self.writer = writer

    async def list_habits(self, user_id: int, include_archived: bool = False) -> list[HabitRecord]:
        query = select(HabitRecord).where(HabitRecord.user_id == user_id)
        if not include_archived:
            query = query.where(HabitRecord.active.is_(True))
        return list((await self.db.scalars(query.order_by(HabitRecord.created_at))).all())

    async def import_legacy(self, user_id: int) -> None:
        """Idempotently retain legacy journal habits and entries as archived history."""
        rows = (
            (
                await self.db.execute(
                    text(
                        "SELECT id, habit, value, notes, date, occurred_at FROM journal_entries "
                        "ORDER BY created_at"
                    )
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return
        existing = {
            row.title: row
            for row in (
                await self.db.scalars(select(HabitRecord).where(HabitRecord.user_id == user_id))
            ).all()
        }
        for legacy in rows:
            title = str(legacy["habit"])
            habit = existing.get(title)
            if habit is None:
                habit = HabitRecord(
                    user_id=user_id,
                    title=title,
                    kind="local",
                    target_type="numeric",
                    target_value=1,
                    weekdays=list(range(7)),
                    active=False,
                )
                self.db.add(habit)
                await self.db.flush()
                existing[title] = habit
            source_name = f"legacy-journal:{legacy['id']}"
            already = await self.db.scalar(
                select(HabitEntryRecord.id).where(HabitEntryRecord.source_name == source_name)
            )
            if already:
                continue
            occurred = legacy["occurred_at"] or f"{legacy['date']}T00:00:00+00:00"
            timestamp = datetime.fromisoformat(str(occurred).replace("Z", "+00:00"))
            try:
                value = float(legacy["value"])
            except (TypeError, ValueError):
                value = 1
            self.db.add(
                HabitEntryRecord(
                    id=uuid5(NAMESPACE_URL, source_name),
                    habit_id=habit.id,
                    user_id=user_id,
                    occurred_at=timestamp,
                    value=value,
                    note=legacy["notes"],
                    source="legacy",
                    source_name=source_name,
                )
            )
        await self.db.commit()

    async def scheduled(self, user_id: int, day: date) -> list[HabitRecord]:
        habits = await self.list_habits(user_id)
        return [habit for habit in habits if day.weekday() in habit.weekdays]

    async def create(self, user_id: int, values: dict[str, object]) -> HabitRecord:
        weekdays = cast(Iterable[int], values.get("weekdays", range(7)))
        values["weekdays"] = validate_weekdays(list(weekdays))
        record = HabitRecord(user_id=user_id, **values)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update(self, user_id: int, habit_id: UUID, values: dict[str, object]) -> HabitRecord:
        habit = await self._habit(user_id, habit_id)
        if "weekdays" in values:
            weekdays = cast(Iterable[int], values["weekdays"])
            values["weekdays"] = validate_weekdays(list(weekdays))
        for key, value in values.items():
            setattr(habit, key, value)
        await self.db.commit()
        await self.db.refresh(habit)
        return habit

    async def archive(self, user_id: int, habit_id: UUID) -> None:
        habit = await self._habit(user_id, habit_id)
        habit.active = False
        await self.db.commit()

    async def create_entry(
        self,
        user_id: int,
        habit_id: UUID,
        occurred_at: datetime,
        value: float,
        note: str | None,
    ) -> HabitEntryRecord:
        habit = await self._habit(user_id, habit_id)
        source_name = None
        source = "local"
        kind = HabitKind(habit.kind)
        if kind is not HabitKind.LOCAL:
            if self.writer is None:
                raise RuntimeError("Google Health writer unavailable")
            remote = await self.writer.create(kind, value, occurred_at)
            source_name = remote.source_name
            source = "google-health"
        entry = HabitEntryRecord(
            habit_id=habit.id,
            user_id=user_id,
            occurred_at=occurred_at,
            value=value,
            note=note,
            source=source,
            source_name=source_name,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def update_entry(
        self, user_id: int, entry_id: UUID, value: float, note: str | None
    ) -> HabitEntryRecord:
        entry = await self._entry(user_id, entry_id)
        habit = await self._habit(user_id, entry.habit_id)
        kind = HabitKind(habit.kind)
        if kind is not HabitKind.LOCAL:
            if self.writer is None or not entry.source_name:
                raise RuntimeError("Google Health writer unavailable")
            await self.writer.update(entry.source_name, kind, value, entry.occurred_at)
        entry.value = value
        entry.note = note
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_entry(self, user_id: int, entry_id: UUID) -> None:
        entry = await self._entry(user_id, entry_id)
        habit = await self._habit(user_id, entry.habit_id)
        kind = HabitKind(habit.kind)
        if kind is not HabitKind.LOCAL:
            if self.writer is None or not entry.source_name:
                raise RuntimeError("Google Health writer unavailable")
            await self.writer.delete(entry.source_name, kind)
        await self.db.delete(entry)
        await self.db.commit()

    async def entries_for_day(
        self, user_id: int, day: date, timezone: ZoneInfo
    ) -> list[HabitEntryRecord]:
        start = datetime.combine(day, time.min, timezone)
        end = datetime.combine(day, time.max, timezone)
        query = select(HabitEntryRecord).where(
            and_(
                HabitEntryRecord.user_id == user_id,
                HabitEntryRecord.occurred_at >= start,
                HabitEntryRecord.occurred_at <= end,
            )
        )
        return list((await self.db.scalars(query.order_by(HabitEntryRecord.occurred_at))).all())

    async def _habit(self, user_id: int, habit_id: UUID) -> HabitRecord:
        record = await self.db.scalar(
            select(HabitRecord).where(HabitRecord.id == habit_id, HabitRecord.user_id == user_id)
        )
        if record is None:
            raise NotFoundError("Habit not found")
        return record

    async def _entry(self, user_id: int, entry_id: UUID) -> HabitEntryRecord:
        record = await self.db.scalar(
            select(HabitEntryRecord).where(
                HabitEntryRecord.id == entry_id, HabitEntryRecord.user_id == user_id
            )
        )
        if record is None:
            raise NotFoundError("Habit entry not found")
        return record
