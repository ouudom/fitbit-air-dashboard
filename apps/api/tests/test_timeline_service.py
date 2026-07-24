from src.modules.timeline.service import _health_label


def test_sleep_timeline_uses_hour_minute_duration() -> None:
    title, detail = _health_label(
        "sleep",
        {"sleep": {"summary": {"minutesAsleep": 405}}},
    )

    assert title == "Sleep"
    assert detail == "6h 45mn"
