from enum import StrEnum


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


SYNC_TYPES = (
    "steps",
    "sleep",
    "exercise",
    "nutrition-log",
    "hydration-log",
    "weight",
    "daily-heart-rate-variability",
    "daily-resting-heart-rate",
    "heart-rate",
    "active-minutes",
)
