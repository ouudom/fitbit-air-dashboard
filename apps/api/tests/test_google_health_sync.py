from datetime import UTC, datetime
from uuid import uuid4

from src.modules.google_health.models import GoogleHealthSyncJob
from src.modules.google_health.sync import _reset_stuck_page, scope_granted


def test_scope_granted_accepts_oauth_url_form() -> None:
    assert scope_granted(
        ["https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly"],
        "googlehealth.health_metrics_and_measurements.readonly",
    )


def test_scope_granted_rejects_different_scope() -> None:
    assert not scope_granted(
        ["https://www.googleapis.com/auth/googlehealth.sleep.readonly"],
        "googlehealth.ecg.readonly",
    )


def test_stuck_page_token_is_reset_after_second_failure() -> None:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    end = datetime(2026, 7, 24, tzinfo=UTC)
    job = GoogleHealthSyncJob(
        connection_id=uuid4(),
        data_type="food",
        fetch_method="list",
        enabled=True,
        poll_interval_minutes=360,
        initial_lookback_days=90,
        incremental_overlap_minutes=60,
        page_size=1000,
        priority=50,
        next_poll_at=start,
        consecutive_failures=1,
        next_page_token="dead-token",
        range_start=start,
        range_end=end,
    )

    _reset_stuck_page(job)
    assert job.next_page_token == "dead-token"

    job.consecutive_failures = 2
    _reset_stuck_page(job)
    assert job.next_page_token is None
    assert job.range_start is None
    assert job.range_end is None
