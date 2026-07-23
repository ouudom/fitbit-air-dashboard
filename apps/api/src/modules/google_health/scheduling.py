import random
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.modules.google_health.types import DataType, PollingTier

QUIET_HOUR_END = 6
FAILURE_DELAYS = (
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
)


def validate_timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Invalid IANA timezone") from exc


def is_quiet_hour(now: datetime, timezone: str) -> bool:
    return now.astimezone(validate_timezone(timezone)).hour < QUIET_HOUR_END


def next_allowed_poll(
    candidate: datetime,
    timezone: str,
    *,
    bypass_quiet_hours: bool = False,
    jitter_minutes: int | None = None,
    randint: Callable[[int, int], int] = random.randint,
) -> datetime:
    if candidate.tzinfo is None:
        raise ValueError("candidate must be timezone-aware")
    if bypass_quiet_hours or not is_quiet_hour(candidate, timezone):
        return candidate.astimezone(UTC)
    local = candidate.astimezone(validate_timezone(timezone))
    jitter = randint(0, 10) if jitter_minutes is None else jitter_minutes
    if not 0 <= jitter <= 10:
        raise ValueError("quiet-hour jitter must be 0 through 10 minutes")
    allowed = datetime.combine(local.date(), time(QUIET_HOUR_END), local.tzinfo)
    return (allowed + timedelta(minutes=jitter)).astimezone(UTC)


def next_regular_poll(
    completed_at: datetime,
    data_type: DataType,
    timezone: str,
    *,
    randint: Callable[[int, int], int] = random.randint,
) -> datetime:
    local = completed_at.astimezone(validate_timezone(timezone))
    if data_type.polling_tier is PollingTier.DAILY:
        next_date = local.date() + timedelta(days=1)
        candidate = datetime.combine(next_date, time(6, 10), local.tzinfo)
        return (candidate + timedelta(minutes=randint(0, 20))).astimezone(UTC)
    candidate = completed_at + timedelta(minutes=data_type.poll_interval_minutes)
    return next_allowed_poll(candidate, timezone, randint=randint)


def daily_noon_retry(
    completed_at: datetime,
    timezone: str,
    *,
    randint: Callable[[int, int], int] = random.randint,
) -> datetime | None:
    local = completed_at.astimezone(validate_timezone(timezone))
    if local.hour >= 12:
        return None
    candidate = datetime.combine(local.date(), time(12), local.tzinfo)
    return (candidate + timedelta(minutes=randint(0, 10))).astimezone(UTC)


def next_failure_poll(
    failed_at: datetime,
    consecutive_failures: int,
    timezone: str,
    *,
    randint: Callable[[int, int], int] = random.randint,
) -> datetime:
    if consecutive_failures < 1:
        raise ValueError("consecutive_failures must be positive")
    delay = FAILURE_DELAYS[min(consecutive_failures - 1, len(FAILURE_DELAYS) - 1)]
    # Spread type-level retries by ±20%, then respect quiet hours.
    jitter_seconds = randint(
        -round(delay.total_seconds() * 0.2), round(delay.total_seconds() * 0.2)
    )
    candidate = failed_at + delay + timedelta(seconds=jitter_seconds)
    return next_allowed_poll(candidate, timezone, randint=randint)


def sync_range(
    now: datetime,
    *,
    initial_lookback_days: int,
    incremental_overlap_minutes: int,
    last_succeeded_at: datetime | None,
    requested_start: datetime | None = None,
    requested_end: datetime | None = None,
) -> tuple[datetime, datetime]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    end = requested_end or now
    if requested_start is not None:
        start = requested_start
    elif last_succeeded_at is None:
        start = end - timedelta(days=initial_lookback_days)
    else:
        start = last_succeeded_at - timedelta(minutes=incremental_overlap_minutes)
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("sync range must be timezone-aware")
    if start >= end:
        raise ValueError("sync range start must precede end")
    return start.astimezone(UTC), end.astimezone(UTC)


def split_date_range(start: date, end: date, maximum_days: int) -> Iterator[tuple[date, date]]:
    if maximum_days < 1:
        raise ValueError("maximum_days must be positive")
    if start > end:
        raise ValueError("start must not follow end")
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=maximum_days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)
