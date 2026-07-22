"""Add FastAPI v1 schema without modifying legacy data."""

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260722_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("email_verified_at", sa.DateTime(timezone=True)),
            sa.Column("password", sa.String(255), nullable=False),
            sa.Column("remember_token", sa.String(100)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    _legacy_tables(existing)

    op.create_table(
        "admin_accounts_v1",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "app_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_agent", sa.Text()),
    )
    op.create_index("ix_app_sessions_user_id", "app_sessions", ["user_id"])
    op.create_index("ix_app_sessions_expires_at", "app_sessions", ["expires_at"])

    op.create_table(
        "google_health_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("health_user_id", sa.Text(), unique=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("scope", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_google_health_connections_user_id", "google_health_connections", ["user_id"]
    )

    op.create_table(
        "google_oauth_states",
        sa.Column("state", sa.String(128), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_google_oauth_states_expires_at", "google_oauth_states", ["expires_at"])

    op.create_table(
        "sync_jobs_v1",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("requested_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_jobs_v1_user_id", "sync_jobs_v1", ["user_id"])
    op.create_index("ix_sync_jobs_v1_status", "sync_jobs_v1", ["status"])

    op.create_table(
        "habits_v1",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="local"),
        sa.Column("target_type", sa.String(16), nullable=False, server_default="boolean"),
        sa.Column("target_value", sa.Float()),
        sa.Column("unit", sa.String(24)),
        sa.Column(
            "weekdays",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default="{0,1,2,3,4,5,6}",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_habits_v1_user_id", "habits_v1", ["user_id"])

    op.create_table(
        "habit_entries_v1",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "habit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("habits_v1.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="1"),
        sa.Column("note", sa.Text()),
        sa.Column("source", sa.String(32), nullable=False, server_default="local"),
        sa.Column("source_name", sa.Text(), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_habit_entries_v1_habit_id", "habit_entries_v1", ["habit_id"])
    op.create_index("ix_habit_entries_v1_user_id", "habit_entries_v1", ["user_id"])
    op.create_index("ix_habit_entries_v1_occurred_at", "habit_entries_v1", ["occurred_at"])


def _legacy_tables(existing: set[str]) -> None:
    definitions: dict[str, Callable[[], None]] = {
        "tokens": lambda: op.create_table(
            "tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("access_token", sa.Text()),
            sa.Column("refresh_token", sa.Text()),
            sa.Column("expiry", sa.BigInteger()),
            sa.Column("scope", sa.Text()),
            sa.Column("updated_at", sa.BigInteger()),
        ),
        "meta": lambda: op.create_table(
            "meta", sa.Column("key", sa.Text(), primary_key=True), sa.Column("value", sa.Text())
        ),
        "daily_metrics": lambda: op.create_table(
            "daily_metrics",
            sa.Column("date", sa.Text(), primary_key=True),
            sa.Column("metric", sa.Text(), primary_key=True),
            sa.Column("value", sa.Float()),
            sa.Column("updated_at", sa.BigInteger()),
        ),
        "health_records": lambda: op.create_table(
            "health_records",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("data_type", sa.Text(), nullable=False),
            sa.Column("start_time", sa.Text()),
            sa.Column("end_time", sa.Text()),
            sa.Column("date", sa.Text()),
            sa.Column("numeric_value", sa.Float()),
            sa.Column("payload", postgresql.JSONB(), nullable=False),
            sa.Column("updated_at", sa.BigInteger()),
        ),
        "exercises": lambda: op.create_table(
            "exercises",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("type", sa.Text()),
            sa.Column("display_name", sa.Text()),
            sa.Column("start_time", sa.Text()),
            sa.Column("duration_s", sa.BigInteger()),
            sa.Column("calories", sa.Float()),
            sa.Column("distance_mm", sa.Float()),
            sa.Column("steps", sa.Integer()),
            sa.Column("avg_hr", sa.Integer()),
            sa.Column("raw", postgresql.JSONB()),
            sa.Column("updated_at", sa.BigInteger()),
        ),
        "sync_state": lambda: op.create_table(
            "sync_state",
            sa.Column("data_type", sa.Text(), primary_key=True),
            sa.Column("last_synced_at", sa.BigInteger()),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("record_count", sa.Integer(), server_default="0"),
            sa.Column("error", sa.Text()),
            sa.Column("updated_at", sa.BigInteger()),
        ),
        "daily_scores": lambda: op.create_table(
            "daily_scores",
            sa.Column("date", sa.Text(), primary_key=True),
            sa.Column("score_type", sa.Text(), primary_key=True),
            sa.Column("model_version", sa.Text(), primary_key=True),
            sa.Column("value", sa.Float()),
            sa.Column("confidence", sa.Text(), nullable=False),
            sa.Column("state", sa.Text(), nullable=False),
            sa.Column("inputs", postgresql.JSONB(), nullable=False),
            sa.Column("explanation", postgresql.JSONB(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        ),
        "journal_entries": lambda: op.create_table(
            "journal_entries",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("date", sa.Text(), nullable=False),
            sa.Column("occurred_at", sa.Text()),
            sa.Column("habit", sa.Text(), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text()),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        ),
    }
    for table, create in definitions.items():
        if table not in existing:
            create()


def downgrade() -> None:
    # Deliberately non-destructive. Health history and compatibility rows remain intact.
    pass
