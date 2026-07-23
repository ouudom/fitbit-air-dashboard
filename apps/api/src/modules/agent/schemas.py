from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Freshness = Literal["fresh", "stale", "unknown"]
Availability = Literal["available", "not-synced", "unavailable"]


class AgentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DateRange(AgentModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_range(self) -> "DateRange":
        if self.start > self.end:
            raise ValueError("start must be on or before end")
        if self.end - self.start > timedelta(days=365):
            raise ValueError("date range cannot exceed 365 days")
        return self


class RecordQuery(DateRange):
    data_types: list[str] | None = Field(default=None, min_length=1, max_length=39)
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=256)

    @model_validator(mode="after")
    def normalize_data_types(self) -> "RecordQuery":
        if self.data_types is not None:
            normalized = list(dict.fromkeys(item.strip() for item in self.data_types))
            if not all(normalized):
                raise ValueError("data types cannot contain blank values")
            self.data_types = normalized
        return self


class TrendQuery(DateRange):
    data_type: str


class SyncCommand(AgentModel):
    days: int = Field(default=30, ge=1, le=365)
    data_types: list[str] | None = Field(default=None, min_length=1, max_length=39)
    start_at: datetime | None = None
    end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "SyncCommand":
        if (self.start_at is None) != (self.end_at is None):
            raise ValueError("start_at and end_at must be provided together")
        if self.start_at is not None and self.end_at is not None:
            if self.start_at.utcoffset() is None or self.end_at.utcoffset() is None:
                raise ValueError("sync timestamps must include a UTC offset")
            if self.start_at >= self.end_at:
                raise ValueError("start_at must be before end_at")
            if self.end_at - self.start_at > timedelta(days=365):
                raise ValueError("sync range cannot exceed 365 days")
            self.start_at = self.start_at.astimezone(UTC)
            self.end_at = self.end_at.astimezone(UTC)
        if self.data_types is not None:
            normalized = list(dict.fromkeys(item.strip() for item in self.data_types))
            if not all(normalized):
                raise ValueError("data types cannot contain blank values")
            self.data_types = normalized
        return self


class Profile(AgentModel):
    name: str
    timezone: str


class Capability(AgentModel):
    data_type: str
    category: str
    granted: bool
    available: bool
    operations: list[str]


class Capabilities(AgentModel):
    source: str = "Google Health"
    items: list[Capability]


class ConnectionStatus(AgentModel):
    connected: bool
    status: str
    granted_scopes: list[str]
    enabled_data_types: int
    total_data_types: int
    last_verified_at: datetime | None = None
    token_expires_at: datetime | None = None


class FreshnessItem(AgentModel):
    data_type: str
    last_synced_at: datetime | None
    freshness: Freshness
    record_count: int


class FreshnessReport(AgentModel):
    source: str = "Google Health"
    items: list[FreshnessItem]


class Metric(AgentModel):
    key: str
    label: str
    value: float | None
    unit: str
    source: str
    observed_at: date
    freshness: Freshness
    availability: Availability


class TimelineItem(AgentModel):
    id: str
    kind: str
    title: str
    occurred_at: datetime
    source: str
    detail: str | None
    freshness: Freshness


class SyncItem(AgentModel):
    data_type: str
    fetch_method: str | None = None
    enabled: bool | None = None
    status: str
    record_count: int
    error: str | None
    next_poll_at: datetime | None = None
    last_attempted_at: datetime | None = None
    last_succeeded_at: datetime | None = None
    updated_at: datetime | None = None


class Today(AgentModel):
    date: date
    timezone: str
    metrics: list[Metric]
    timeline: list[TimelineItem]
    sync: list[SyncItem]


class Timeline(AgentModel):
    date: date
    timezone: str
    items: list[TimelineItem]


class HealthRecord(AgentModel):
    id: UUID
    data_type: str
    record_date: date | None
    started_at: datetime | None
    ended_at: datetime | None
    provider_name: str | None
    source_family: str | None
    source: str = "Google Health"
    last_synced_at: datetime
    freshness: Freshness
    value: float | None
    payload: dict[str, object]


class RecordPage(AgentModel):
    items: list[HealthRecord]
    next_cursor: str | None


class SummaryMetric(AgentModel):
    data_type: str
    value: float | None
    record_count: int
    last_synced_at: datetime | None
    freshness: Freshness
    availability: Availability


class Summary(AgentModel):
    start: date
    end: date
    source: str = "Google Health"
    derivation: str = "LifeStats projection"
    metrics: list[SummaryMetric]


class TrendPoint(AgentModel):
    date: date
    value: float | None
    record_count: int


class Trend(AgentModel):
    data_type: str
    start: date
    end: date
    source: str = "Google Health"
    derivation: str = "LifeStats projection"
    points: list[TrendPoint]


class ExerciseExport(AgentModel):
    exercise_id: UUID
    format: Literal["tcx"] = "tcx"
    availability: Availability
    reason: str | None = None
    content: str | None = None


class SyncStatus(AgentModel):
    connection_id: UUID
    status: str
    items: list[SyncItem]


class SyncQueued(AgentModel):
    status: Literal["queued"] = "queued"
    data_types: list[str]


class UnavailableOperation(AgentModel):
    availability: Literal["unavailable"] = "unavailable"
    reason: str


class ConnectionStart(AgentModel):
    authorization_url: str


class DisconnectResult(AgentModel):
    status: str
    cache_retained: bool
