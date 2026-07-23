"""Add compact public-client OAuth persistence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260723_0004"
down_revision = "20260723_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", sa.String(80), nullable=False, unique=True),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column(
            "redirect_uris",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_oauth_clients_client_id", "oauth_clients", ["client_id"])
    op.create_index("ix_oauth_clients_revoked_at", "oauth_clients", ["revoked_at"])

    op.create_table(
        "oauth_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "oauth_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "oauth_client_id",
            "user_id",
            "resource",
            name="uq_oauth_grants_client_user_resource",
        ),
    )
    op.create_index("ix_oauth_grants_oauth_client_id", "oauth_grants", ["oauth_client_id"])
    op.create_index("ix_oauth_grants_user_id", "oauth_grants", ["user_id"])
    op.create_index("ix_oauth_grants_revoked_at", "oauth_grants", ["revoked_at"])

    op.create_table(
        "oauth_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("oauth_grants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("value_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("redirect_uri", sa.Text()),
        sa.Column("code_challenge", sa.String(128)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind IN ('authorization_code', 'access_token', 'refresh_token')",
            name="ck_oauth_credentials_kind",
        ),
    )
    op.create_index("ix_oauth_credentials_grant_id", "oauth_credentials", ["grant_id"])
    op.create_index("ix_oauth_credentials_kind", "oauth_credentials", ["kind"])
    op.create_index("ix_oauth_credentials_expires_at", "oauth_credentials", ["expires_at"])
    op.create_index("ix_oauth_credentials_revoked_at", "oauth_credentials", ["revoked_at"])


def downgrade() -> None:
    # Deliberately non-destructive. Credential removal is a manual operator action.
    pass
