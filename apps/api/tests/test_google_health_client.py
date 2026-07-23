from datetime import UTC, datetime

import httpx
from src.modules.google_health.client import _retry_after_seconds, _retry_delay


def test_retry_after_seconds_is_honored() -> None:
    response = httpx.Response(429, headers={"Retry-After": "17"})
    assert _retry_delay(0, response) == 17


def test_retry_after_http_date_is_supported() -> None:
    now = datetime(2026, 7, 23, 0, 0, tzinfo=UTC)
    assert (
        _retry_after_seconds(
            "Thu, 23 Jul 2026 00:00:30 GMT",
            now=now,
        )
        == 30
    )


def test_full_jitter_respects_exponential_ceiling() -> None:
    called_with: tuple[float, float] | None = None

    def uniform(start: float, end: float) -> float:
        nonlocal called_with
        called_with = (start, end)
        return end

    assert _retry_delay(3, uniform=uniform) == 8
    assert called_with == (0, 8)
