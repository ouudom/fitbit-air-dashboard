from pathlib import Path

MIGRATIONS = Path(__file__).parents[1] / "alembic" / "versions"
AGENT_TOKEN_MIGRATION = MIGRATIONS / "20260723_0002_agent_tokens.py"
LEGACY_OAUTH_MIGRATION = MIGRATIONS / "20260723_0003_agent_oauth_clients.py"
COMPACT_OAUTH_MIGRATION = MIGRATIONS / "20260723_0004_compact_public_oauth.py"
MCP_TOKEN_MIGRATION = MIGRATIONS / "20260724_0005_mcp_query_tokens.py"


def test_query_token_migration_renames_table_and_removes_oauth_tables() -> None:
    source = MCP_TOKEN_MIGRATION.read_text()

    assert 'down_revision = "20260723_0004"' in source
    assert 'op.rename_table("agent_tokens", "mcp_tokens")' in source
    assert source.count("op.drop_table(") == 7
    assert '"oauth_credentials"' in source
    assert '"oauth_grants"' in source
    assert '"oauth_clients"' in source
    assert '"agent_oauth_clients"' in source


def test_historical_migrations_remain_unchanged_and_present() -> None:
    assert AGENT_TOKEN_MIGRATION.exists()
    assert LEGACY_OAUTH_MIGRATION.exists()
    assert COMPACT_OAUTH_MIGRATION.exists()
