"""Add per-user OAuth clients and short-lived access tokens."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260723_0003"
down_revision = "20260723_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_oauth_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("client_id", sa.String(80), nullable=False, unique=True),
        sa.Column("client_secret_hash", sa.String(64), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_agent_oauth_clients_user_id", "agent_oauth_clients", ["user_id"])
    op.create_index("ix_agent_oauth_clients_client_id", "agent_oauth_clients", ["client_id"])
    op.create_index("ix_agent_oauth_clients_expires_at", "agent_oauth_clients", ["expires_at"])
    op.create_index("ix_agent_oauth_clients_revoked_at", "agent_oauth_clients", ["revoked_at"])

    op.create_table(
        "agent_oauth_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oauth_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_agent_oauth_access_tokens_oauth_client_id",
        "agent_oauth_access_tokens",
        ["oauth_client_id"],
    )
    op.create_index(
        "ix_agent_oauth_access_tokens_expires_at",
        "agent_oauth_access_tokens",
        ["expires_at"],
    )

    op.create_table(
        "agent_oauth_authorization_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oauth_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_agent_oauth_authorization_codes_oauth_client_id",
        "agent_oauth_authorization_codes",
        ["oauth_client_id"],
    )
    op.create_index(
        "ix_agent_oauth_authorization_codes_expires_at",
        "agent_oauth_authorization_codes",
        ["expires_at"],
    )

    op.create_table(
        "agent_oauth_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oauth_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_agent_oauth_refresh_tokens_oauth_client_id",
        "agent_oauth_refresh_tokens",
        ["oauth_client_id"],
    )
    op.create_index(
        "ix_agent_oauth_refresh_tokens_expires_at",
        "agent_oauth_refresh_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    # Deliberately non-destructive. Credential removal is a manual operator action.
    pass
