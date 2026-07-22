from lifestats.google_health.application.sync import _number, _point_date


def test_rollup_ignores_civil_date_numbers() -> None:
    point = {
        "civilStartTime": {"date": {"year": 2026, "month": 7, "day": 22}},
        "civilEndTime": {"date": {"year": 2026, "month": 7, "day": 22}},
        "steps": {"countSum": "3822"},
    }
    assert _point_date(point) == "2026-07-22"
    assert _number(point) == 3822


def test_daily_hrv_uses_measurement_not_date() -> None:
    payload = {
        "date": {"year": 2026, "month": 7, "day": 22},
        "dailyAverageHeartRateVariabilityMilliseconds": 47.5,
    }
    assert _number(payload) == 47.5
