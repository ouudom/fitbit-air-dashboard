from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from src.core.config import Settings
from src.core.errors import NotFoundError
from src.modules.agent.schemas import DateRange, HealthRecord, RecordQuery, SyncCommand
from src.modules.agent.service import AgentService


def test_agent_ranges_and_pagination_are_bounded() -> None:
    with pytest.raises(ValidationError):
        DateRange(start=date(2026, 7, 2), end=date(2026, 7, 1))
    with pytest.raises(ValidationError):
        DateRange(start=date(2025, 1, 1), end=date(2026, 7, 1))
    with pytest.raises(ValidationError):
        RecordQuery(
            start=date(2026, 7, 1),
            end=date(2026, 7, 2),
            limit=101,
        )


def test_sync_command_requires_complete_aware_bounded_window() -> None:
    with pytest.raises(ValidationError):
        SyncCommand(start_at=datetime(2026, 7, 1, tzinfo=UTC))
    with pytest.raises(ValidationError):
        SyncCommand(
            start_at=datetime(2026, 7, 1),
            end_at=datetime(2026, 7, 2),
        )
    command = SyncCommand(
        start_at=datetime(2026, 7, 1, tzinfo=UTC),
        end_at=datetime(2026, 7, 2, tzinfo=UTC),
        data_types=["sleep", "sleep", "steps"],
    )
    assert command.data_types == ["sleep", "steps"]


@pytest.mark.asyncio
async def test_single_record_lookup_always_filters_by_user() -> None:
    record_id = uuid4()
    record = SimpleNamespace(
        id=record_id,
        data_type="exercise",
        record_date=date(2026, 7, 1),
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        ended_at=datetime(2026, 7, 1, 1, tzinfo=UTC),
        provider_name="providers/example",
        source_family="watch",
        last_synced_at=datetime.now(UTC),
        raw_payload={"exercise": {"activeDuration": "3600s"}},
    )

    class Database:
        statement = None

        async def scalar(self, statement: object) -> object:
            self.statement = statement
            return record

    db = Database()
    service = AgentService(db, Settings(app_env="test"))  # type: ignore[arg-type]
    result = await service.get_exercise(42, record_id)

    compiled = db.statement.compile(  # type: ignore[union-attr]
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    assert "gh_connections.user_id = 42" in str(compiled)
    assert result.id == record_id


@pytest.mark.asyncio
async def test_generic_query_rejects_unknown_type_before_database_access() -> None:
    service = AgentService(object(), Settings(app_env="test"))  # type: ignore[arg-type]
    request = RecordQuery(
        start=date(2026, 7, 1),
        end=date(2026, 7, 2),
        data_types=["invented-score"],
    )

    with pytest.raises(NotFoundError, match="invented-score"):
        await service.query_health_data(1, request)


@pytest.mark.asyncio
async def test_exercise_export_reports_unavailable_without_inventing_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_id = uuid4()
    record = HealthRecord(
        id=record_id,
        data_type="exercise",
        record_date=date(2026, 7, 1),
        started_at=None,
        ended_at=None,
        provider_name=None,
        source_family=None,
        last_synced_at=datetime.now(UTC),
        freshness="fresh",
        value=None,
        payload={"exercise": {"displayName": "Run"}},
    )
    service = AgentService(object(), Settings(app_env="test"))  # type: ignore[arg-type]

    async def one(*_: object) -> HealthRecord:
        return record

    monkeypatch.setattr(service, "_one", one)
    result = await service.get_exercise_export(1, record_id)

    assert result.availability == "unavailable"
    assert result.content is None
    assert "projection" in (result.reason or "")


@pytest.mark.asyncio
async def test_trigger_sync_preserves_authenticated_user_scope() -> None:
    calls: list[tuple[int, object]] = []

    async def queue_sync(user_id: int, payload: object) -> list[str]:
        calls.append((user_id, payload))
        return ["sleep"]

    service = AgentService(object(), Settings(app_env="test"))  # type: ignore[arg-type]
    service.google_health = SimpleNamespace(queue_sync=queue_sync)  # type: ignore[assignment]
    result = await service.trigger_sync(77, SyncCommand(days=7, data_types=["sleep"]))

    assert result.data_types == ["sleep"]
    assert calls[0][0] == 77


def test_date_range_allows_exact_365_days() -> None:
    start = date(2025, 7, 1)
    result = DateRange(start=start, end=start + timedelta(days=365))
    assert result.end - result.start == timedelta(days=365)
