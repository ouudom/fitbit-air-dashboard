"""Create the fresh LifeStats database schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260723_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    _create_users()
    _create_sessions()
    _create_connections()
    _create_sync_job()
    _create_records()
    _create_webhook_events()


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "timezone",
            sa.String(64),
            nullable=False,
            server_default="Asia/Phnom_Penh",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def _create_sessions() -> None:
    op.create_table(
        "sessions",
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
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index("ix_sessions_revoked_at", "sessions", ["revoked_at"])


def _create_connections() -> None:
    op.create_table(
        "gh_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Nullable during the OAuth callback before users/me/identity returns.
        sa.Column("provider_user_id", sa.Text(), unique=True),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("refresh_token_ciphertext", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_gh_connections_user_id", "gh_connections", ["user_id"], unique=True)


def _create_sync_job() -> None:
    op.create_table(
        "gh_sync_job",
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gh_connections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data_type", sa.Text(), primary_key=True),
        sa.Column("fetch_method", sa.String(20), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("poll_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("initial_lookback_days", sa.Integer(), nullable=False),
        sa.Column("incremental_overlap_minutes", sa.Integer(), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="50"),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("range_start", sa.DateTime(timezone=True)),
        sa.Column("range_end", sa.DateTime(timezone=True)),
        sa.Column("next_page_token", sa.Text()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("record_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
        sa.Column("last_succeeded_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_gh_sync_job_enabled_next_poll_at",
        "gh_sync_job",
        ["enabled", "next_poll_at"],
    )
    op.create_index(
        "ix_gh_sync_job_status_lease_until",
        "gh_sync_job",
        ["status", "lease_until"],
    )


def _create_records() -> None:
    op.create_table(
        "gh_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gh_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data_type", sa.Text(), nullable=False),
        sa.Column("record_type", sa.String(20), nullable=False),
        sa.Column("fetch_method", sa.String(20), nullable=False),
        sa.Column("provider_name", sa.Text()),
        sa.Column("identity_hash", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("record_date", sa.Date()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("source_family", sa.Text()),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "first_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "connection_id",
            "data_type",
            "fetch_method",
            "identity_hash",
            name="uq_gh_records_identity",
        ),
    )
    op.create_index(
        "ix_gh_records_connection_type_date",
        "gh_records",
        ["connection_id", "data_type", "record_date"],
    )
    op.create_index(
        "ix_gh_records_connection_type_started",
        "gh_records",
        ["connection_id", "data_type", "started_at"],
    )
    op.create_index("ix_gh_records_provider_name", "gh_records", ["provider_name"])


def _create_webhook_events() -> None:
    op.create_table(
        "gh_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gh_connections.id", ondelete="SET NULL"),
        ),
        sa.Column("provider_user_id", sa.Text(), nullable=False),
        sa.Column("provider_subscription_name", sa.Text()),
        sa.Column("data_type_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("operation", sa.String(32)),
        sa.Column("interval_start", sa.DateTime(timezone=True)),
        sa.Column("interval_end", sa.DateTime(timezone=True)),
        sa.Column("civil_start_date", sa.Date()),
        sa.Column("civil_end_date", sa.Date()),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text()),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("event_hash", name="uq_gh_webhook_events_event_hash"),
    )
    op.create_index("ix_gh_webhook_events_status", "gh_webhook_events", ["status"])
    op.create_index(
        "ix_gh_webhook_events_received_at",
        "gh_webhook_events",
        ["received_at"],
    )
    op.create_index(
        "ix_gh_webhook_events_provider_user_id",
        "gh_webhook_events",
        ["provider_user_id"],
    )


def downgrade() -> None:
    # Deliberately non-destructive. Database deletion is a manual operator action.
    pass
