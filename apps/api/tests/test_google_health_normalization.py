from datetime import UTC, date, datetime

import pytest
from src.modules.google_health.normalization import normalize_record
from src.modules.google_health.types import DATA_TYPE_REGISTRY


def test_identifiable_point_uses_provider_name_for_identity() -> None:
    first = {
        "name": "users/u/dataTypes/weight/dataPoints/one",
        "dataSource": {"platform": "FITBIT"},
        "weight": {
            "sampleTime": {"physicalTime": "2026-07-23T06:30:00+07:00"},
            "weightGrams": 72_400,
        },
    }
    corrected = {
        **first,
        "weight": {
            **first["weight"],
            "weightGrams": 72_300,
        },
    }
    original = normalize_record(DATA_TYPE_REGISTRY["weight"], first)
    update = normalize_record(DATA_TYPE_REGISTRY["weight"], corrected)
    assert original.identity_hash == update.identity_hash
    assert original.payload_hash != update.payload_hash
    assert original.started_at == datetime(2026, 7, 22, 23, 30, tzinfo=UTC)


def test_daily_rollup_identity_uses_civil_date_and_source() -> None:
    item = {
        "civilStartTime": {"date": {"year": 2026, "month": 7, "day": 23}},
        "dataSourceFamily": {"name": "users/me/dataSourceFamilies/all-sources"},
        "totalCalories": {"kilocaloriesSum": 2200},
    }
    record = normalize_record(DATA_TYPE_REGISTRY["total-calories"], item)
    assert record.record_date == date(2026, 7, 23)
    assert record.source_family == "users/me/dataSourceFamilies/all-sources"


def test_record_without_stable_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="stable identity"):
        normalize_record(DATA_TYPE_REGISTRY["weight"], {"weight": {"weightGrams": 72_400}})


def test_payload_hash_is_independent_of_json_key_order() -> None:
    left = {
        "name": "one",
        "weight": {
            "weightGrams": 72_400,
            "sampleTime": {"physicalTime": "2026-07-23T00:00:00Z"},
        },
    }
    right = {
        "weight": {
            "sampleTime": {"physicalTime": "2026-07-23T00:00:00Z"},
            "weightGrams": 72_400,
        },
        "name": "one",
    }
    assert (
        normalize_record(DATA_TYPE_REGISTRY["weight"], left).payload_hash
        == normalize_record(DATA_TYPE_REGISTRY["weight"], right).payload_hash
    )
