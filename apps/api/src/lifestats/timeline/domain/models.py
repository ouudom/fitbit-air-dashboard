from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimelineItem:
    id: str
    kind: str
    title: str
    occurred_at: datetime
    source: str
    detail: str | None = None
    freshness: str = "fresh"
