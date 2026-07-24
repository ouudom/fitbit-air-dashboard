from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID
from zoneinfo import ZoneInfo

from src.modules.dashboard.service import _insights_from_records, _sleep_detail_from_record


def test_sleep_detail_exposes_stages_and_deduplicates_summary() -> None:
    stage_summary = [
        {"type": "AWAKE", "minutes": "104", "count": "4"},
        {"type": "LIGHT", "minutes": "200", "count": "14"},
        {"type": "DEEP", "minutes": "83", "count": "4"},
        {"type": "REM", "minutes": "66", "count": "8"},
    ]
    record = SimpleNamespace(
        id=UUID("5aca88c2-0825-4676-a7c0-4b2c59ff4fb7"),
        started_at=datetime(2026, 7, 23, 17, 58, tzinfo=UTC),
        ended_at=datetime(2026, 7, 24, 1, 31, tzinfo=UTC),
        last_synced_at=datetime(2026, 7, 24, 9, 45, tzinfo=UTC),
        raw_payload={
            "sleep": {
                "interval": {
                    "startTime": "2026-07-23T17:58:00Z",
                    "endTime": "2026-07-24T01:31:00Z",
                },
                "stages": [
                    {
                        "type": "DEEP",
                        "startTime": "2026-07-23T18:19:30Z",
                        "endTime": "2026-07-23T18:41:30Z",
                    }
                ],
                "summary": {
                    "minutesInSleepPeriod": "453",
                    "minutesAsleep": "349",
                    "minutesAwake": "104",
                    "minutesToFallAsleep": "0",
                    "minutesAfterWakeUp": "0",
                    "stagesSummary": stage_summary + stage_summary,
                },
            }
        },
    )

    detail = _sleep_detail_from_record(record)

    assert detail is not None
    assert detail["minutesAsleep"] == 349
    assert detail["sleepEfficiency"] == 77.0
    assert detail["stageSummary"] == [
        {"type": "AWAKE", "minutes": 104, "count": 4},
        {"type": "REM", "minutes": 66, "count": 8},
        {"type": "LIGHT", "minutes": 200, "count": 14},
        {"type": "DEEP", "minutes": 83, "count": 4},
    ]
    assert detail["stages"] == [
        {
            "type": "DEEP",
            "startAt": datetime(2026, 7, 23, 18, 19, 30, tzinfo=UTC),
            "endAt": datetime(2026, 7, 23, 18, 41, 30, tzinfo=UTC),
        }
    ]


def test_sleep_detail_requires_session_interval() -> None:
    record = SimpleNamespace(
        id=UUID("5aca88c2-0825-4676-a7c0-4b2c59ff4fb7"),
        started_at=None,
        ended_at=None,
        last_synced_at=datetime(2026, 7, 24, 9, 45, tzinfo=UTC),
        raw_payload={"sleep": {"summary": {"minutesAsleep": "349"}}},
    )

    assert _sleep_detail_from_record(record) is None


def test_insights_aggregate_steps_and_sleep_by_wake_date() -> None:
    records = [
        SimpleNamespace(
            data_type="steps",
            record_date=date(2026, 7, 24),
            started_at=datetime(2026, 7, 24, 2, 10, tzinfo=UTC),
            last_synced_at=datetime(2026, 7, 24, 9, 45, tzinfo=UTC),
            raw_payload={"steps": {"count": {"value": "1200"}}},
        ),
        SimpleNamespace(
            data_type="steps",
            record_date=date(2026, 7, 24),
            started_at=datetime(2026, 7, 24, 2, 40, tzinfo=UTC),
            last_synced_at=datetime(2026, 7, 24, 9, 45, tzinfo=UTC),
            raw_payload={"steps": {"count": {"value": "361"}}},
        ),
        SimpleNamespace(
            id=UUID("5aca88c2-0825-4676-a7c0-4b2c59ff4fb7"),
            data_type="sleep",
            record_date=None,
            started_at=datetime(2026, 7, 23, 17, 58, tzinfo=UTC),
            ended_at=datetime(2026, 7, 24, 1, 31, tzinfo=UTC),
            last_synced_at=datetime(2026, 7, 24, 9, 45, tzinfo=UTC),
            raw_payload={
                "sleep": {
                    "interval": {
                        "startTime": "2026-07-23T17:58:00Z",
                        "endTime": "2026-07-24T01:31:00Z",
                    },
                    "summary": {
                        "minutesInSleepPeriod": "453",
                        "minutesAsleep": "349",
                        "minutesAwake": "104",
                        "stagesSummary": [
                            {"type": "DEEP", "minutes": "83", "count": "4"},
                            {"type": "LIGHT", "minutes": "200", "count": "14"},
                            {"type": "REM", "minutes": "66", "count": "8"},
                        ],
                    },
                }
            },
        ),
    ]

    insights = _insights_from_records(
        records,
        date(2026, 7, 18),
        date(2026, 7, 24),
        ZoneInfo("Asia/Phnom_Penh"),
    )

    assert insights["steps"] == [{"date": "2026-07-24", "value": 1561}]
    assert insights["stepBuckets"] == [
        {
            "startedAt": datetime(2026, 7, 24, 9, tzinfo=ZoneInfo("Asia/Phnom_Penh")),
            "value": 1561,
        }
    ]
    assert insights["sleep"] == [
        {
            "date": "2026-07-24",
            "minutesAsleep": 349,
            "minutesInSleepPeriod": 453,
            "minutesAwake": 104,
            "sleepEfficiency": 77.0,
            "minutesDeep": 83,
            "minutesLight": 200,
            "minutesRem": 66,
            "startAt": datetime(2026, 7, 23, 17, 58, tzinfo=UTC),
            "endAt": datetime(2026, 7, 24, 1, 31, tzinfo=UTC),
        }
    ]
