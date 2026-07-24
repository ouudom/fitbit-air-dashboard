from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from src.core.config import Settings
from src.modules.google_health.client import (
    GoogleHealthClient,
    _retry_after_seconds,
    _retry_delay,
)
from src.modules.google_health.registry import DATA_TYPE_REGISTRY


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


@pytest.mark.asyncio
async def test_electrocardiogram_uses_supported_lower_bound_filter() -> None:
    client = GoogleHealthClient(AsyncMock(), Settings(), user_id=1)
    request = AsyncMock(return_value={"dataPoints": []})
    with patch.object(client, "request", request):
        pages = [
            page
            async for page in client.point_pages(
                DATA_TYPE_REGISTRY["electrocardiogram"],
                date(2026, 7, 1),
                date(2026, 7, 24),
            )
        ]
    await client.close()

    assert pages == [([], None)]
    assert request.await_args.kwargs["params"] == {
        "pageSize": 1000,
        "filter": ('electrocardiogram.interval.start_time >= "2026-07-01T00:00:00Z"'),
    }


@pytest.mark.asyncio
async def test_nutrition_log_uses_explicit_civil_datetime_filter() -> None:
    client = GoogleHealthClient(AsyncMock(), Settings(), user_id=1)
    request = AsyncMock(return_value={"dataPoints": []})
    with patch.object(client, "request", request):
        pages = [
            page
            async for page in client.point_pages(
                DATA_TYPE_REGISTRY["nutrition-log"],
                date(2026, 7, 1),
                date(2026, 7, 24),
            )
        ]
    await client.close()

    assert pages == [([], None)]
    assert request.await_args.kwargs["params"] == {
        "pageSize": 1000,
        "filter": (
            'nutrition_log.sample_time.civil_time >= "2026-07-01T00:00:00" '
            'AND nutrition_log.sample_time.civil_time < "2026-07-25T00:00:00"'
        ),
    }
