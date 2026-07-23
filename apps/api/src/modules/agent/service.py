import base64
import binascii
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.errors import NotFoundError
from src.modules.agent.schemas import (
    Availability,
    Capabilities,
    Capability,
    ConnectionStart,
    ConnectionStatus,
    DateRange,
    DisconnectResult,
    ExerciseExport,
    Freshness,
    FreshnessItem,
    FreshnessReport,
    HealthRecord,
    Metric,
    Profile,
    RecordPage,
    RecordQuery,
    Summary,
    SummaryMetric,
    SyncCommand,
    SyncItem,
    SyncQueued,
    SyncStatus,
    Timeline,
    TimelineItem,
    Today,
    Trend,
    TrendPoint,
    TrendQuery,
)
from src.modules.auth.models import User
from src.modules.dashboard.service import DashboardService
from src.modules.google_health.models import (
    GoogleHealthConnection,
    GoogleHealthRecord,
)
from src.modules.google_health.normalization import extract_number
from src.modules.google_health.oauth import OAuthService
from src.modules.google_health.registry import (
    ACTIVITY_SCOPE,
    DATA_TYPE_REGISTRY,
    ECG_SCOPE,
    HEALTH_SCOPE,
    IRN_SCOPE,
    NUTRITION_SCOPE,
    SLEEP_SCOPE,
)
from src.modules.google_health.schemas import SyncRequest
from src.modules.google_health.service import GoogleHealthService
from src.modules.timeline.service import TimelineService

FITNESS_TYPES = frozenset(
    key for key, item in DATA_TYPE_REGISTRY.items() if item.scope == ACTIVITY_SCOPE
)
SLEEP_TYPES = frozenset(
    key for key, item in DATA_TYPE_REGISTRY.items() if item.scope == SLEEP_SCOPE
)
NUTRITION_TYPES = frozenset(
    key for key, item in DATA_TYPE_REGISTRY.items() if item.scope == NUTRITION_SCOPE
)
SENSITIVE_TYPES = frozenset({"electrocardiogram", "irregular-rhythm-notification"})
HEALTH_TYPES = frozenset(
    key
    for key, item in DATA_TYPE_REGISTRY.items()
    if item.scope == HEALTH_SCOPE and key not in SENSITIVE_TYPES
)
BODY_MEASUREMENT_TYPES = frozenset({"body-fat", "height", "weight"})
HEART_RATE_ZONE_TYPES = frozenset(
    {"calories-in-heart-rate-zone", "daily-heart-rate-zones", "time-in-heart-rate-zone"}
)


class AgentService:
    """Typed, user-scoped orchestration for agent transports."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.google_health = GoogleHealthService(db, settings)

    async def get_profile(self, user_id: int) -> Profile:
        user = await self.db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise NotFoundError("User not found")
        return Profile(name=user.name, timezone=user.timezone)

    async def list_capabilities(self, user_id: int) -> Capabilities:
        connection = await self._connection(user_id)
        granted_scopes = set(connection.scopes) if connection else set()
        rows = await self._record_counts(user_id)
        return Capabilities(
            items=[
                Capability(
                    data_type=data_type,
                    category=_category(item.scope),
                    granted=_scope_granted(item.scope, granted_scopes),
                    available=rows.get(data_type, 0) > 0,
                    operations=list(item.supported_operations),
                )
                for data_type, item in DATA_TYPE_REGISTRY.items()
            ]
        )

    async def get_google_health_status(self, user_id: int) -> ConnectionStatus:
        raw = await self.google_health.integration_status(user_id)
        return ConnectionStatus(
            connected=bool(raw["connected"]),
            status=str(raw["status"]),
            granted_scopes=cast(list[str], raw["grantedScopes"]),
            enabled_data_types=_int(raw["enabledDataTypes"]),
            total_data_types=_int(raw["totalDataTypes"]),
            last_verified_at=_datetime(raw.get("lastVerifiedAt")),
            token_expires_at=_datetime(raw.get("tokenExpiresAt")),
        )

    async def get_connection_status(self, user_id: int) -> ConnectionStatus:
        return await self.get_google_health_status(user_id)

    async def start_google_health_connection(self, user_id: int) -> ConnectionStart:
        url = await OAuthService(self.db, self.settings).authorization_url(user_id)
        return ConnectionStart(authorization_url=url)

    async def disconnect_google_health(self, user_id: int) -> DisconnectResult:
        raw = await self.google_health.disconnect(user_id)
        return DisconnectResult(
            status=str(raw["status"]),
            cache_retained=bool(raw["cacheRetained"]),
        )

    async def get_data_freshness(self, user_id: int) -> FreshnessReport:
        query = (
            select(
                GoogleHealthRecord.data_type,
                func.max(GoogleHealthRecord.last_synced_at),
                func.count(GoogleHealthRecord.id),
            )
            .join(
                GoogleHealthConnection,
                GoogleHealthConnection.id == GoogleHealthRecord.connection_id,
            )
            .where(
                GoogleHealthConnection.user_id == user_id,
                GoogleHealthRecord.deleted_at.is_(None),
            )
            .group_by(GoogleHealthRecord.data_type)
        )
        values = {row[0]: (row[1], row[2]) for row in (await self.db.execute(query)).all()}
        return FreshnessReport(
            items=[
                FreshnessItem(
                    data_type=data_type,
                    last_synced_at=values.get(data_type, (None, 0))[0],
                    freshness=_freshness(values.get(data_type, (None, 0))[0]),
                    record_count=values.get(data_type, (None, 0))[1],
                )
                for data_type in DATA_TYPE_REGISTRY
            ]
        )

    async def get_today(self, user_id: int, day: date | None = None) -> Today:
        raw = await DashboardService(self.db, self.settings).get(user_id, day)
        raw_metrics = cast(list[dict[str, object]], raw["metrics"])
        raw_timeline = cast(list[dict[str, object]], raw["timeline"])
        raw_sync = cast(list[dict[str, object]], raw["sync"])
        return Today(
            date=date.fromisoformat(str(raw["date"])),
            timezone=str(raw["timezone"]),
            metrics=[
                Metric(
                    key=str(item["key"]),
                    label=str(item["label"]),
                    value=_optional_float(item["value"]),
                    unit=str(item["unit"]),
                    source=str(item["source"]),
                    observed_at=date.fromisoformat(str(item["observedAt"])),
                    freshness=_freshness_literal(item["freshness"]),
                    availability=_availability_literal(item["availability"]),
                )
                for item in raw_metrics
            ],
            timeline=[_timeline_from_mapping(item) for item in raw_timeline],
            sync=[
                SyncItem(
                    data_type=str(item["dataType"]),
                    status=str(item["status"]),
                    record_count=_int(item["recordCount"]),
                    error=_optional_string(item["error"]),
                    last_succeeded_at=_datetime(item["lastSyncedAt"]),
                )
                for item in raw_sync
            ],
        )

    async def get_timeline(self, user_id: int, day: date | None = None) -> Timeline:
        profile = await self.get_profile(user_id)
        try:
            timezone = ZoneInfo(profile.timezone)
        except ZoneInfoNotFoundError:
            timezone = ZoneInfo(self.settings.app_timezone)
        selected = day or datetime.now(timezone).date()
        rows = await TimelineService(self.db).for_day(user_id, selected, timezone)
        return Timeline(
            date=selected,
            timezone=timezone.key,
            items=[
                TimelineItem(
                    id=row.id,
                    kind=row.kind,
                    title=row.title,
                    occurred_at=row.occurred_at,
                    source=row.source,
                    detail=row.detail,
                    freshness=_freshness_literal(row.freshness),
                )
                for row in rows
            ],
        )

    async def get_fitness_summary(self, user_id: int, request: DateRange) -> Summary:
        return await self._summary(user_id, request, FITNESS_TYPES)

    async def list_exercises(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, {"exercise"})

    async def get_exercise(self, user_id: int, record_id: UUID) -> HealthRecord:
        return await self._one(user_id, record_id, {"exercise"})

    async def get_activity_trend(self, user_id: int, request: TrendQuery) -> Trend:
        self._require_type(request.data_type, FITNESS_TYPES)
        return await self._trend(user_id, request)

    async def get_heart_rate_zones(self, user_id: int, request: DateRange) -> Summary:
        return await self._summary(user_id, request, HEART_RATE_ZONE_TYPES)

    async def get_exercise_export(self, user_id: int, record_id: UUID) -> ExerciseExport:
        record = await self._one(user_id, record_id, {"exercise"})
        content = _find_tcx(record.payload)
        if content is None:
            return ExerciseExport(
                exercise_id=record_id,
                availability="unavailable",
                reason="TCX export is not present in the synced projection",
            )
        return ExerciseExport(
            exercise_id=record_id,
            availability="available",
            content=content,
        )

    async def get_sleep_summary(self, user_id: int, request: DateRange) -> Summary:
        return await self._summary(user_id, request, SLEEP_TYPES)

    async def list_sleep_sessions(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, {"sleep"})

    async def get_sleep_session(self, user_id: int, record_id: UUID) -> HealthRecord:
        return await self._one(user_id, record_id, {"sleep"})

    async def get_sleep_trend(self, user_id: int, request: DateRange) -> Trend:
        return await self._trend(
            user_id,
            TrendQuery(start=request.start, end=request.end, data_type="sleep"),
        )

    async def get_health_summary(self, user_id: int, request: DateRange) -> Summary:
        return await self._summary(user_id, request, HEALTH_TYPES)

    async def get_measurement_latest(self, user_id: int, data_type: str) -> HealthRecord:
        self._require_type(data_type, HEALTH_TYPES | BODY_MEASUREMENT_TYPES)
        query = self._base_records(user_id, {data_type}).order_by(
            GoogleHealthRecord.started_at.desc().nullslast(),
            GoogleHealthRecord.record_date.desc().nullslast(),
            GoogleHealthRecord.last_synced_at.desc(),
        )
        row = await self.db.scalar(query.limit(1))
        if row is None:
            raise NotFoundError(f"No synced {data_type} measurement")
        return _record(row)

    async def get_measurement_trend(self, user_id: int, request: TrendQuery) -> Trend:
        self._require_type(request.data_type, HEALTH_TYPES | BODY_MEASUREMENT_TYPES)
        return await self._trend(user_id, request)

    async def query_health_data(self, user_id: int, request: RecordQuery) -> RecordPage:
        selected = set(request.data_types or DATA_TYPE_REGISTRY)
        unknown = selected - DATA_TYPE_REGISTRY.keys()
        if unknown:
            detail = ", ".join(sorted(unknown))
            raise NotFoundError(f"Unsupported Google Health data type: {detail}")
        return await self._page(user_id, request, selected)

    async def list_irregular_rhythm_notifications(
        self, user_id: int, request: RecordQuery
    ) -> RecordPage:
        return await self._page(user_id, request, {"irregular-rhythm-notification"})

    async def list_electrocardiograms(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, {"electrocardiogram"})

    async def get_electrocardiogram(self, user_id: int, record_id: UUID) -> HealthRecord:
        return await self._one(user_id, record_id, {"electrocardiogram"})

    async def get_nutrition_summary(self, user_id: int, request: DateRange) -> Summary:
        return await self._summary(user_id, request, NUTRITION_TYPES)

    async def list_nutrition_logs(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, {"nutrition-log"})

    async def list_hydration_logs(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, {"hydration-log"})

    async def get_body_measurements(self, user_id: int, request: RecordQuery) -> RecordPage:
        return await self._page(user_id, request, BODY_MEASUREMENT_TYPES)

    async def get_sync_status(self, user_id: int) -> SyncStatus:
        raw = await self.google_health.sync_jobs(user_id)
        items = cast(list[dict[str, object]], raw["items"])
        return SyncStatus(
            connection_id=UUID(str(raw["connectionId"])),
            status=str(raw["status"]),
            items=[_sync_item(item) for item in items],
        )

    async def get_data_type_sync_status(self, user_id: int, data_type: str) -> SyncItem:
        return _sync_item(await self.google_health.sync_status(user_id, data_type))

    async def trigger_sync(self, user_id: int, command: SyncCommand) -> SyncQueued:
        selected = await self.google_health.queue_sync(
            user_id,
            SyncRequest(
                days=command.days,
                data_types=command.data_types,
                start_at=command.start_at,
                end_at=command.end_at,
            ),
        )
        return SyncQueued(data_types=selected)

    async def _summary(
        self, user_id: int, request: DateRange, data_types: set[str] | frozenset[str]
    ) -> Summary:
        rows = await self._records(user_id, request, data_types)
        grouped: dict[str, list[GoogleHealthRecord]] = defaultdict(list)
        for row in rows:
            grouped[row.data_type].append(row)
        metrics: list[SummaryMetric] = []
        for data_type in sorted(data_types):
            typed = grouped[data_type]
            values = [
                value for row in typed if (value := extract_number(row.raw_payload)) is not None
            ]
            last_synced_at = max((row.last_synced_at for row in typed), default=None)
            metrics.append(
                SummaryMetric(
                    data_type=data_type,
                    value=sum(values) if values else None,
                    record_count=len(typed),
                    last_synced_at=last_synced_at,
                    freshness=_freshness(last_synced_at),
                    availability="available" if typed else "not-synced",
                )
            )
        return Summary(start=request.start, end=request.end, metrics=metrics)

    async def _trend(self, user_id: int, request: TrendQuery) -> Trend:
        rows = await self._records(user_id, request, {request.data_type})
        grouped: dict[date, list[float]] = defaultdict(list)
        counts: dict[date, int] = defaultdict(int)
        for row in rows:
            observed = row.record_date or (row.started_at.date() if row.started_at else None)
            if observed is None:
                continue
            counts[observed] += 1
            value = extract_number(row.raw_payload)
            if value is not None:
                grouped[observed].append(value)
        return Trend(
            data_type=request.data_type,
            start=request.start,
            end=request.end,
            points=[
                TrendPoint(
                    date=day,
                    value=sum(grouped[day]) if grouped[day] else None,
                    record_count=counts[day],
                )
                for day in sorted(counts)
            ],
        )

    async def _page(
        self,
        user_id: int,
        request: RecordQuery,
        allowed_types: set[str] | frozenset[str],
    ) -> RecordPage:
        selected = set(request.data_types or allowed_types)
        disallowed = selected - allowed_types
        if disallowed:
            raise NotFoundError(f"Unsupported data type for tool: {', '.join(sorted(disallowed))}")
        offset = _decode_cursor(request.cursor)
        query = (
            self._records_query(user_id, request, selected)
            .order_by(
                GoogleHealthRecord.started_at.desc().nullslast(),
                GoogleHealthRecord.record_date.desc().nullslast(),
                GoogleHealthRecord.id,
            )
            .offset(offset)
            .limit(request.limit + 1)
        )
        rows = list((await self.db.scalars(query)).all())
        has_more = len(rows) > request.limit
        items = rows[: request.limit]
        return RecordPage(
            items=[_record(row) for row in items],
            next_cursor=_encode_cursor(offset + request.limit) if has_more else None,
        )

    async def _one(
        self,
        user_id: int,
        record_id: UUID,
        allowed_types: set[str] | frozenset[str],
    ) -> HealthRecord:
        row = await self.db.scalar(
            self._base_records(user_id, allowed_types).where(GoogleHealthRecord.id == record_id)
        )
        if row is None:
            raise NotFoundError("Google Health record not found")
        return _record(row)

    async def _records(
        self,
        user_id: int,
        request: DateRange,
        data_types: set[str] | frozenset[str],
    ) -> list[GoogleHealthRecord]:
        query = self._records_query(user_id, request, data_types)
        return list((await self.db.scalars(query)).all())

    def _records_query(
        self,
        user_id: int,
        request: DateRange,
        data_types: set[str] | frozenset[str],
    ) -> Select[tuple[GoogleHealthRecord]]:
        utc_start = datetime.combine(request.start, time.min, UTC)
        utc_end = datetime.combine(request.end + timedelta(days=1), time.min, UTC)
        return self._base_records(user_id, data_types).where(
            or_(
                GoogleHealthRecord.record_date.between(request.start, request.end),
                (
                    (GoogleHealthRecord.started_at >= utc_start)
                    & (GoogleHealthRecord.started_at < utc_end)
                ),
            )
        )

    @staticmethod
    def _base_records(
        user_id: int, data_types: set[str] | frozenset[str]
    ) -> Select[tuple[GoogleHealthRecord]]:
        return (
            select(GoogleHealthRecord)
            .join(
                GoogleHealthConnection,
                GoogleHealthConnection.id == GoogleHealthRecord.connection_id,
            )
            .where(
                GoogleHealthConnection.user_id == user_id,
                GoogleHealthRecord.data_type.in_(data_types),
                GoogleHealthRecord.deleted_at.is_(None),
            )
        )

    async def _connection(self, user_id: int) -> GoogleHealthConnection | None:
        return cast(
            GoogleHealthConnection | None,
            await self.db.scalar(
                select(GoogleHealthConnection).where(GoogleHealthConnection.user_id == user_id)
            ),
        )

    async def _record_counts(self, user_id: int) -> dict[str, int]:
        query = (
            select(GoogleHealthRecord.data_type, func.count(GoogleHealthRecord.id))
            .join(
                GoogleHealthConnection,
                GoogleHealthConnection.id == GoogleHealthRecord.connection_id,
            )
            .where(
                GoogleHealthConnection.user_id == user_id,
                GoogleHealthRecord.deleted_at.is_(None),
            )
            .group_by(GoogleHealthRecord.data_type)
        )
        return {row[0]: row[1] for row in (await self.db.execute(query)).all()}

    @staticmethod
    def _require_type(data_type: str, allowed: set[str] | frozenset[str]) -> None:
        if data_type not in allowed:
            raise NotFoundError(f"Unsupported data type for tool: {data_type}")


def _category(scope: str) -> str:
    return {
        ACTIVITY_SCOPE: "fitness",
        SLEEP_SCOPE: "sleep",
        NUTRITION_SCOPE: "nutrition",
        ECG_SCOPE: "ecg",
        IRN_SCOPE: "irregular-rhythm",
    }.get(scope, "health")


def _scope_granted(required: str, granted: set[str]) -> bool:
    return required in granted or any(item.endswith(f"/auth/{required}") for item in granted)


def _freshness(updated_at: datetime | None) -> Freshness:
    if updated_at is None:
        return "unknown"
    normalized = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - normalized.astimezone(UTC)
    return "stale" if age > timedelta(days=1) else "fresh"


def _record(row: GoogleHealthRecord) -> HealthRecord:
    return HealthRecord(
        id=row.id,
        data_type=row.data_type,
        record_date=row.record_date,
        started_at=row.started_at,
        ended_at=row.ended_at,
        provider_name=row.provider_name,
        source_family=row.source_family,
        last_synced_at=row.last_synced_at,
        freshness=_freshness_literal(_freshness(row.last_synced_at)),
        value=extract_number(row.raw_payload),
        payload=row.raw_payload,
    )


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        value = int(decoded)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ValueError("Invalid pagination cursor") from exc
    if value < 0:
        raise ValueError("Invalid pagination cursor")
    return value


def _find_tcx(payload: dict[str, object]) -> str | None:
    for key in ("tcx", "tcxContent", "tcx_content"):
        value = payload.get(key)
        if isinstance(value, str) and value.lstrip().startswith("<?xml"):
            return value
    return None


def _timeline_from_mapping(item: object) -> TimelineItem:
    if not isinstance(item, dict):
        raise TypeError("Invalid dashboard timeline item")
    return TimelineItem(
        id=str(item["id"]),
        kind=str(item["kind"]),
        title=str(item["title"]),
        occurred_at=datetime.fromisoformat(str(item["occurredAt"])),
        source=str(item["source"]),
        detail=_optional_string(item["detail"]),
        freshness=_freshness_literal(item["freshness"]),
    )


def _sync_item(item: object) -> SyncItem:
    if not isinstance(item, dict):
        raise TypeError("Invalid sync item")
    return SyncItem(
        data_type=str(item["dataType"]),
        fetch_method=_optional_string(item.get("fetchMethod")),
        enabled=_optional_bool(item.get("enabled")),
        status=str(item["status"]),
        record_count=int(item["recordCount"]),
        error=_optional_string(item.get("error")),
        next_poll_at=_datetime(item.get("nextPollAt")),
        last_attempted_at=_datetime(item.get("lastAttemptedAt")),
        last_succeeded_at=_datetime(item.get("lastSucceededAt")),
        updated_at=_datetime(item.get("updatedAt")),
    )


def _datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError("Expected numeric value")


def _optional_bool(value: object) -> bool | None:
    return None if value is None else bool(value)


def _freshness_literal(value: object) -> Freshness:
    normalized = str(value)
    if normalized == "fresh":
        return "fresh"
    if normalized == "stale":
        return "stale"
    return "unknown"


def _availability_literal(value: object) -> Availability:
    normalized = str(value)
    if normalized == "available":
        return "available"
    if normalized == "not-synced":
        return "not-synced"
    return "unavailable"


def _int(value: object) -> int:
    if isinstance(value, (int, str)):
        return int(value)
    raise TypeError("Expected integer value")
