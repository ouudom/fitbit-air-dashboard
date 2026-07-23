from datetime import UTC, datetime, timedelta

import pytest
from src.modules.google_health.registry import DATA_TYPE_REGISTRY
from src.modules.google_health.scheduling import (
    daily_noon_retry,
    is_quiet_hour,
    next_allowed_poll,
    next_failure_poll,
    next_regular_poll,
    sync_range,
)


def test_quiet_hours_use_user_timezone() -> None:
    instant = datetime(2026, 7, 22, 18, 30, tzinfo=UTC)
    assert is_quiet_hour(instant, "Asia/Phnom_Penh")
    assert not is_quiet_hour(instant, "UTC")


def test_scheduled_poll_defers_to_six_with_jitter() -> None:
    instant = datetime(2026, 7, 22, 18, 30, tzinfo=UTC)
    assert next_allowed_poll(instant, "Asia/Phnom_Penh", jitter_minutes=7) == datetime(
        2026, 7, 22, 23, 7, tzinfo=UTC
    )


def test_manual_poll_bypasses_quiet_hours() -> None:
    instant = datetime(2026, 7, 22, 18, 30, tzinfo=UTC)
    assert next_allowed_poll(instant, "Asia/Phnom_Penh", bypass_quiet_hours=True) == instant


def test_daily_poll_runs_next_morning() -> None:
    completed = datetime(2026, 7, 23, 3, tzinfo=UTC)
    result = next_regular_poll(
        completed,
        DATA_TYPE_REGISTRY["daily-resting-heart-rate"],
        "Asia/Phnom_Penh",
        randint=lambda _start, _end: 5,
    )
    assert result == datetime(2026, 7, 23, 23, 15, tzinfo=UTC)


def test_empty_daily_result_retries_at_noon() -> None:
    completed = datetime(2026, 7, 22, 23, 15, tzinfo=UTC)
    assert daily_noon_retry(
        completed,
        "Asia/Phnom_Penh",
        randint=lambda _start, _end: 5,
    ) == datetime(2026, 7, 23, 5, 5, tzinfo=UTC)


@pytest.mark.parametrize(
    ("failures", "delay"),
    [
        (1, timedelta(minutes=5)),
        (2, timedelta(minutes=15)),
        (3, timedelta(hours=1)),
        (4, timedelta(hours=6)),
        (10, timedelta(hours=6)),
    ],
)
def test_failure_schedule(failures: int, delay: timedelta) -> None:
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    assert next_failure_poll(now, failures, "UTC", randint=lambda _start, _end: 0) == now + delay


def test_initial_and_incremental_ranges() -> None:
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)
    assert sync_range(
        now,
        initial_lookback_days=90,
        incremental_overlap_minutes=120,
        last_succeeded_at=None,
    ) == (now - timedelta(days=90), now)
    last = now - timedelta(minutes=15)
    assert sync_range(
        now,
        initial_lookback_days=90,
        incremental_overlap_minutes=120,
        last_succeeded_at=last,
    ) == (last - timedelta(minutes=120), now)
