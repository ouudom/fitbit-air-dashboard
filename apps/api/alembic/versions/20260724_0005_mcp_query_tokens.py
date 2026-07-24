"""Use MCP query tokens and remove OAuth persistence."""

from alembic import op

revision = "20260724_0005"
down_revision = "20260723_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("agent_tokens", "mcp_tokens")
    op.execute("ALTER INDEX IF EXISTS ix_agent_tokens_user_id RENAME TO ix_mcp_tokens_user_id")
    op.execute(
        "ALTER INDEX IF EXISTS ix_agent_tokens_token_prefix RENAME TO ix_mcp_tokens_token_prefix"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_agent_tokens_expires_at RENAME TO ix_mcp_tokens_expires_at"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_agent_tokens_revoked_at RENAME TO ix_mcp_tokens_revoked_at"
    )

    op.drop_table("oauth_credentials")
    op.drop_table("oauth_grants")
    op.drop_table("oauth_clients")

    op.drop_table("agent_oauth_access_tokens")
    op.drop_table("agent_oauth_authorization_codes")
    op.drop_table("agent_oauth_refresh_tokens")
    op.drop_table("agent_oauth_clients")


def downgrade() -> None:
    raise RuntimeError("OAuth table removal is destructive and cannot be downgraded automatically")
