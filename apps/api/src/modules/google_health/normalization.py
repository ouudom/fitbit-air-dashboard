import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from src.modules.google_health.types import DataType


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    provider_name: str | None
    identity_hash: str
    payload_hash: str
    record_date: date | None
    started_at: datetime | None
    ended_at: datetime | None
    source_family: str | None
    provider_updated_at: datetime | None
    raw_payload: dict[str, Any]


def normalize_record(data_type: DataType, item: dict[str, Any]) -> NormalizedRecord:
    provider_name = _string(item, "name") or _string(item, "dataPointName")
    inner = item.get(data_type.payload_field)
    payload = inner if isinstance(inner, dict) else item
    source_family = (
        _string(item, "dataSourceFamily.name")
        or _string(item, "dataSource.family")
        or _string(item, "dataSource.name")
        or _string(item, "dataSource.platform")
    )
    record_date = _civil_date(
        payload,
        "date",
        "civilStartTime.date",
        "interval.civilStartTime.date",
        "sampleTime.civilTime.date",
    ) or _civil_date(item, "civilStartTime.date")
    started_at = _timestamp(
        payload,
        "interval.startTime",
        "sampleTime.physicalTime",
        "startTime",
    ) or _timestamp(item, "startTime")
    ended_at = _timestamp(payload, "interval.endTime", "endTime") or _timestamp(item, "endTime")
    provider_updated_at = _timestamp(
        item,
        "updateTime",
        "updatedTime",
        "lastModifiedTime",
    )
    identity = _identity_parts(
        data_type.endpoint_id,
        provider_name,
        source_family,
        record_date,
        started_at,
        ended_at,
    )
    canonical = _canonical_json(item)
    return NormalizedRecord(
        provider_name=provider_name,
        identity_hash=_sha256(identity),
        payload_hash=_sha256(canonical),
        record_date=record_date,
        started_at=started_at,
        ended_at=ended_at,
        source_family=source_family,
        provider_updated_at=provider_updated_at,
        raw_payload=item,
    )


def _identity_parts(
    endpoint_id: str,
    provider_name: str | None,
    source_family: str | None,
    record_date: date | None,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> str:
    if provider_name:
        return f"name|{endpoint_id}|{provider_name}"
    if record_date:
        return f"date|{endpoint_id}|{source_family or ''}|{record_date.isoformat()}"
    if started_at:
        return (
            f"time|{endpoint_id}|{source_family or ''}|{started_at.isoformat()}|"
            f"{ended_at.isoformat() if ended_at else ''}"
        )
    raise ValueError(f"{endpoint_id} record has no stable identity fields")


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _nested(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        current = current.get(part) if isinstance(current, dict) else None
    return current


def _string(value: dict[str, Any], path: str) -> str | None:
    result = _nested(value, path)
    return result if isinstance(result, str) and result else None


def _timestamp(value: dict[str, Any], *paths: str) -> datetime | None:
    for path in paths:
        raw = _string(value, path)
        if not raw:
            continue
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError(f"Provider timestamp lacks UTC offset: {raw}")
        return parsed.astimezone(UTC)
    return None


def _civil_date(value: dict[str, Any], *paths: str) -> date | None:
    for path in paths:
        raw = _nested(value, path)
        if isinstance(raw, str):
            return date.fromisoformat(raw[:10])
        if isinstance(raw, dict) and all(key in raw for key in ("year", "month", "day")):
            return date(int(raw["year"]), int(raw["month"]), int(raw["day"]))
    return None
