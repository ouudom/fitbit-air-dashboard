from datetime import datetime

from pydantic import BaseModel


class MetricResponse(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str
    source: str
    observedAt: str
    freshness: str
    availability: str


class TimelineItemResponse(BaseModel):
    id: str
    kind: str
    title: str
    occurredAt: str
    source: str
    detail: str | None
    freshness: str


class SyncStateResponse(BaseModel):
    dataType: str
    status: str
    lastSyncedAt: str | None
    recordCount: int
    error: str | None


class SleepStageSegmentResponse(BaseModel):
    type: str
    startAt: datetime
    endAt: datetime


class SleepStageSummaryResponse(BaseModel):
    type: str
    minutes: int
    count: int


class SleepDetailResponse(BaseModel):
    sessionId: str
    startAt: datetime
    endAt: datetime
    minutesInSleepPeriod: int | None
    minutesAsleep: int | None
    minutesAwake: int | None
    minutesToFallAsleep: int | None
    minutesAfterWakeUp: int | None
    sleepEfficiency: float | None
    stages: list[SleepStageSegmentResponse]
    stageSummary: list[SleepStageSummaryResponse]
    source: str
    freshness: str
    availability: str
    derivation: str
    lastSyncedAt: datetime


class DashboardResponse(BaseModel):
    date: str
    timezone: str
    metrics: list[MetricResponse]
    timeline: list[TimelineItemResponse]
    sync: list[SyncStateResponse]
    sleep: SleepDetailResponse | None
