from sqlalchemy import UniqueConstraint
from src.core.database import Base
from src.modules.auth.models import Session, User
from src.modules.google_health.models import (
    GhWebhookEvent,
    GoogleHealthConnection,
    GoogleHealthRecord,
    GoogleHealthSyncJob,
)


def test_v2_tables_are_registered_without_legacy_auth_tables() -> None:
    expected = {
        "users",
        "sessions",
        "gh_connections",
        "gh_sync_job",
        "gh_records",
        "gh_webhook_events",
    }
    assert expected == set(Base.metadata.tables)


def test_user_timezone_and_session_lifecycle_columns() -> None:
    assert User.__table__.c.timezone.nullable is False
    assert User.__table__.c.timezone.server_default is not None
    assert {"last_seen_at", "revoked_at", "ip_address"} <= set(Session.__table__.c.keys())


def test_sync_job_uses_per_type_composite_identity() -> None:
    table = GoogleHealthSyncJob.__table__
    assert [column.name for column in table.primary_key.columns] == [
        "connection_id",
        "data_type",
        "fetch_method",
    ]
    assert {"next_poll_at", "next_page_token", "lease_until", "last_succeeded_at"} <= set(
        table.c.keys()
    )


def test_record_identity_and_raw_payload_are_persisted() -> None:
    table = GoogleHealthRecord.__table__
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert (
        "connection_id",
        "data_type",
        "fetch_method",
        "identity_hash",
    ) in unique_columns
    assert table.c.raw_payload.nullable is False
    assert "deleted_at" in table.c.keys()


def test_webhook_inbox_has_deduplication_and_interval_fields() -> None:
    table = GhWebhookEvent.__table__
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("event_hash",) in unique_columns
    assert {
        "operation",
        "interval_start",
        "interval_end",
        "civil_start_date",
        "civil_end_date",
        "raw_payload",
    } <= set(table.c.keys())


def test_connection_uses_ciphertext_columns() -> None:
    columns = GoogleHealthConnection.__table__.c
    assert columns.access_token_ciphertext.nullable is False
    assert {"provider_user_id", "refresh_token_ciphertext", "scopes", "status"} <= set(
        columns.keys()
    )
