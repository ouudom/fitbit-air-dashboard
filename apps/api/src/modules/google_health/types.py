from dataclasses import dataclass
from enum import StrEnum


class FetchMethod(StrEnum):
    LIST = "list"
    RECONCILE = "reconcile"
    DAILY_ROLLUP = "daily_rollup"


class RecordKind(StrEnum):
    DAILY = "daily"
    FOOD = "food"
    INTERVAL = "interval"
    ROLLUP = "rollup"
    SAMPLE = "sample"
    SESSION = "session"


class PollingTier(StrEnum):
    ACTIVITY = "activity"
    DAILY = "daily"
    MEASUREMENT = "measurement"
    RARE = "rare"
    RECENT_EVENT = "recent_event"


ACTIVITY_SCOPE = "googlehealth.activity_and_fitness.readonly"
ECG_SCOPE = "googlehealth.ecg.readonly"
HEALTH_SCOPE = "googlehealth.health_metrics_and_measurements.readonly"
IRN_SCOPE = "googlehealth.irn.readonly"
NUTRITION_SCOPE = "googlehealth.nutrition.readonly"
SLEEP_SCOPE = "googlehealth.sleep.readonly"


@dataclass(frozen=True, slots=True)
class DataType:
    endpoint_id: str
    payload_field: str
    record_kind: RecordKind
    scope: str
    fetch_method: FetchMethod
    supported_operations: tuple[str, ...]
    filter_field: str | None
    page_size: int
    maximum_range_days: int
    polling_tier: PollingTier
    poll_interval_minutes: int
    initial_lookback_days: int
    incremental_overlap_minutes: int
    priority: int
    webhook_supported: bool = False
    true_zero: bool = False


def _filter(payload_field: str, kind: RecordKind) -> str | None:
    snake = _snake_case(payload_field)
    if kind is RecordKind.DAILY:
        return f"{snake}.date"
    if kind is RecordKind.INTERVAL or kind is RecordKind.SESSION:
        return f"{snake}.interval.civil_start_time"
    if kind is RecordKind.SAMPLE:
        return f"{snake}.sample_time.civil_time"
    return None


def _snake_case(value: str) -> str:
    result = ""
    for character in value:
        if character.isupper():
            result += f"_{character.lower()}"
        else:
            result += character
    return result


def _type(
    endpoint_id: str,
    payload_field: str,
    kind: RecordKind,
    scope: str,
    *,
    fetch_method: FetchMethod = FetchMethod.RECONCILE,
    tier: PollingTier = PollingTier.MEASUREMENT,
    filter_field: str | None = "",
    webhook_supported: bool = False,
    true_zero: bool = False,
) -> DataType:
    intervals = {
        PollingTier.ACTIVITY: (15, 120, 10),
        PollingTier.RECENT_EVENT: (30, 7 * 24 * 60, 20),
        PollingTier.MEASUREMENT: (60, 7 * 24 * 60, 30),
        PollingTier.DAILY: (24 * 60, 14 * 24 * 60, 40),
        PollingTier.RARE: (6 * 60, 30 * 24 * 60, 50),
    }
    poll_interval, overlap, priority = intervals[tier]
    page_size = 25 if endpoint_id in {"sleep", "exercise"} else 1000
    maximum_range_days = (
        14
        if endpoint_id
        in {
            "active-minutes",
            "calories-in-heart-rate-zone",
            "heart-rate",
            "total-calories",
        }
        else 90
    )
    aggregate_types = {
        "active-energy-burned",
        "active-minutes",
        "active-zone-minutes",
        "altitude",
        "blood-glucose",
        "body-fat",
        "calories-in-heart-rate-zone",
        "core-body-temperature",
        "distance",
        "floors",
        "heart-rate",
        "height",
        "hydration-log",
        "nutrition-log",
        "run-vo2-max",
        "sedentary-period",
        "steps",
        "swim-lengths-data",
        "time-in-heart-rate-zone",
        "total-calories",
        "weight",
    }
    supported_operations = [fetch_method.value]
    if endpoint_id in aggregate_types:
        supported_operations.extend(["rollup", "daily_rollup"])
    if endpoint_id == "exercise":
        supported_operations.append("export_exercise_tcx")
    resolved_filter = _filter(payload_field, kind) if filter_field == "" else filter_field
    return DataType(
        endpoint_id=endpoint_id,
        payload_field=payload_field,
        record_kind=RecordKind.ROLLUP if fetch_method is FetchMethod.DAILY_ROLLUP else kind,
        scope=scope,
        fetch_method=fetch_method,
        supported_operations=tuple(dict.fromkeys(supported_operations)),
        filter_field=resolved_filter,
        page_size=page_size,
        maximum_range_days=maximum_range_days,
        polling_tier=tier,
        poll_interval_minutes=poll_interval,
        initial_lookback_days=90,
        incremental_overlap_minutes=overlap,
        priority=priority,
        webhook_supported=webhook_supported,
        true_zero=true_zero,
    )


DATA_TYPES = (
    _type(
        "active-energy-burned",
        "activeEnergyBurned",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        true_zero=True,
    ),
    _type(
        "active-minutes",
        "activeMinutes",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        true_zero=True,
    ),
    _type(
        "active-zone-minutes",
        "activeZoneMinutes",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        true_zero=True,
    ),
    _type(
        "activity-level",
        "activityLevel",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
    ),
    _type("altitude", "altitude", RecordKind.INTERVAL, ACTIVITY_SCOPE),
    _type("blood-glucose", "bloodGlucose", RecordKind.SAMPLE, HEALTH_SCOPE),
    _type("body-fat", "bodyFat", RecordKind.SAMPLE, HEALTH_SCOPE),
    _type(
        "calories-in-heart-rate-zone",
        "caloriesInHeartRateZone",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        fetch_method=FetchMethod.DAILY_ROLLUP,
        tier=PollingTier.DAILY,
        true_zero=True,
    ),
    _type(
        "core-body-temperature",
        "coreBodyTemperature",
        RecordKind.SAMPLE,
        HEALTH_SCOPE,
    ),
    _type(
        "daily-heart-rate-variability",
        "dailyHeartRateVariability",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-heart-rate-zones",
        "dailyHeartRateZones",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-oxygen-saturation",
        "dailyOxygenSaturation",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-respiratory-rate",
        "dailyRespiratoryRate",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-resting-heart-rate",
        "dailyRestingHeartRate",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-sleep-temperature-derivations",
        "dailySleepTemperatureDerivations",
        RecordKind.DAILY,
        HEALTH_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "daily-vo2-max",
        "dailyVo2Max",
        RecordKind.DAILY,
        ACTIVITY_SCOPE,
        tier=PollingTier.DAILY,
    ),
    _type(
        "distance",
        "distance",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        true_zero=True,
    ),
    _type(
        "electrocardiogram",
        "electrocardiogram",
        RecordKind.SESSION,
        ECG_SCOPE,
        fetch_method=FetchMethod.LIST,
        tier=PollingTier.RARE,
    ),
    _type(
        "exercise",
        "exercise",
        RecordKind.SESSION,
        ACTIVITY_SCOPE,
        tier=PollingTier.RECENT_EVENT,
        webhook_supported=True,
    ),
    _type(
        "floors",
        "floors",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        true_zero=True,
    ),
    _type(
        "food",
        "food",
        RecordKind.FOOD,
        NUTRITION_SCOPE,
        fetch_method=FetchMethod.LIST,
        tier=PollingTier.RARE,
        filter_field=None,
    ),
    _type(
        "food-measurement-unit",
        "foodMeasurementUnit",
        RecordKind.FOOD,
        NUTRITION_SCOPE,
        fetch_method=FetchMethod.LIST,
        tier=PollingTier.RARE,
        filter_field=None,
    ),
    _type(
        "heart-rate",
        "heartRate",
        RecordKind.SAMPLE,
        HEALTH_SCOPE,
        tier=PollingTier.ACTIVITY,
        webhook_supported=True,
    ),
    _type(
        "heart-rate-variability",
        "heartRateVariability",
        RecordKind.SAMPLE,
        HEALTH_SCOPE,
    ),
    _type("height", "height", RecordKind.SAMPLE, HEALTH_SCOPE, tier=PollingTier.RARE),
    _type(
        "hydration-log",
        "hydrationLog",
        RecordKind.SESSION,
        NUTRITION_SCOPE,
        tier=PollingTier.RECENT_EVENT,
        webhook_supported=True,
    ),
    _type(
        "irregular-rhythm-notification",
        "irregularRhythmNotification",
        RecordKind.SESSION,
        IRN_SCOPE,
        fetch_method=FetchMethod.LIST,
        tier=PollingTier.RARE,
    ),
    _type(
        "nutrition-log",
        "nutritionLog",
        RecordKind.SAMPLE,
        NUTRITION_SCOPE,
        tier=PollingTier.RECENT_EVENT,
        webhook_supported=True,
    ),
    _type("oxygen-saturation", "oxygenSaturation", RecordKind.SAMPLE, HEALTH_SCOPE),
    _type(
        "respiratory-rate-sleep-summary",
        "respiratoryRateSleepSummary",
        RecordKind.SAMPLE,
        HEALTH_SCOPE,
    ),
    _type("run-vo2-max", "runVo2Max", RecordKind.SAMPLE, ACTIVITY_SCOPE),
    _type(
        "sedentary-period",
        "sedentaryPeriod",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
    ),
    _type(
        "sleep",
        "sleep",
        RecordKind.SESSION,
        SLEEP_SCOPE,
        tier=PollingTier.RECENT_EVENT,
        filter_field="sleep.interval.civil_end_time",
        webhook_supported=True,
    ),
    _type(
        "steps",
        "steps",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        tier=PollingTier.ACTIVITY,
        webhook_supported=True,
        true_zero=True,
    ),
    _type(
        "swim-lengths-data",
        "swimLengthsData",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
    ),
    _type(
        "time-in-heart-rate-zone",
        "timeInHeartRateZone",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
    ),
    _type(
        "total-calories",
        "totalCalories",
        RecordKind.INTERVAL,
        ACTIVITY_SCOPE,
        fetch_method=FetchMethod.DAILY_ROLLUP,
        tier=PollingTier.DAILY,
        true_zero=True,
    ),
    _type("vo2-max", "vo2Max", RecordKind.SAMPLE, ACTIVITY_SCOPE),
    _type("weight", "weight", RecordKind.SAMPLE, HEALTH_SCOPE),
)

DATA_TYPE_REGISTRY = {item.endpoint_id: item for item in DATA_TYPES}
SYNC_TYPES = tuple(DATA_TYPE_REGISTRY)


def validate_registry() -> None:
    if len(DATA_TYPES) != 39:
        raise ValueError(f"Expected 39 Google Health data types, got {len(DATA_TYPES)}")
    if len(DATA_TYPE_REGISTRY) != len(DATA_TYPES):
        raise ValueError("Google Health endpoint IDs must be unique")
    for item in DATA_TYPES:
        if item.fetch_method.value not in item.supported_operations:
            raise ValueError(f"Preferred fetch is unsupported for {item.endpoint_id}")
        maximum_page_size = 25 if item.endpoint_id in {"sleep", "exercise"} else 10_000
        if not 1 <= item.page_size <= maximum_page_size:
            raise ValueError(f"Invalid page size for {item.endpoint_id}")
        expected_range = (
            14
            if item.endpoint_id
            in {
                "active-minutes",
                "calories-in-heart-rate-zone",
                "heart-rate",
                "total-calories",
            }
            else 90
        )
        if item.maximum_range_days != expected_range:
            raise ValueError(f"Invalid maximum range for {item.endpoint_id}")


validate_registry()
