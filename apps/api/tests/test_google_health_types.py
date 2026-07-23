import pytest
from src.modules.google_health.types import (
    DATA_TYPE_REGISTRY,
    DATA_TYPES,
    FetchMethod,
    validate_registry,
)


def test_registry_has_all_39_unique_types() -> None:
    validate_registry()
    assert len(DATA_TYPES) == 39
    assert len(DATA_TYPE_REGISTRY) == 39


def test_non_reconciled_types_use_list() -> None:
    expected = {
        "electrocardiogram",
        "food",
        "food-measurement-unit",
        "irregular-rhythm-notification",
    }
    actual = {item.endpoint_id for item in DATA_TYPES if item.fetch_method is FetchMethod.LIST}
    assert actual == expected


def test_rollup_only_types_use_daily_rollup() -> None:
    expected = {"calories-in-heart-rate-zone", "total-calories"}
    actual = {
        item.endpoint_id for item in DATA_TYPES if item.fetch_method is FetchMethod.DAILY_ROLLUP
    }
    assert actual == expected


@pytest.mark.parametrize("data_type", ["sleep", "exercise"])
def test_session_page_size_is_capped(data_type: str) -> None:
    assert DATA_TYPE_REGISTRY[data_type].page_size == 25


def test_constrained_ranges_are_14_days() -> None:
    constrained = {
        "active-minutes",
        "calories-in-heart-rate-zone",
        "heart-rate",
        "total-calories",
    }
    assert {item.endpoint_id for item in DATA_TYPES if item.maximum_range_days == 14} == constrained


def test_registry_declares_supported_operations() -> None:
    assert DATA_TYPE_REGISTRY["exercise"].supported_operations == (
        "reconcile",
        "export_exercise_tcx",
    )
    assert DATA_TYPE_REGISTRY["steps"].supported_operations == (
        "reconcile",
        "rollup",
        "daily_rollup",
    )
