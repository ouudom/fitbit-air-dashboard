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


class ScoreResponse(BaseModel):
    key: str
    label: str
    value: float | None
    status: str
    modelVersion: str
    components: dict[str, float]
    missingInputs: list[str]
    explanation: str
    disclaimer: str


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


class DashboardResponse(BaseModel):
    date: str
    timezone: str
    metrics: list[MetricResponse]
    scores: list[ScoreResponse]
    timeline: list[TimelineItemResponse]
    sync: list[SyncStateResponse]
