from src.modules.google_health.normalization import extract_number


def test_rollup_ignores_civil_date_numbers() -> None:
    point = {
        "civilStartTime": {"date": {"year": 2026, "month": 7, "day": 22}},
        "civilEndTime": {"date": {"year": 2026, "month": 7, "day": 22}},
        "steps": {"countSum": "3822"},
    }
    assert extract_number(point) == 3822


def test_daily_hrv_uses_measurement_not_date() -> None:
    payload = {
        "date": {"year": 2026, "month": 7, "day": 22},
        "dailyAverageHeartRateVariabilityMilliseconds": 47.5,
    }
    assert extract_number(payload) == 47.5
