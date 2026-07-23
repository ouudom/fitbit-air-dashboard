from pathlib import Path

MIGRATIONS = Path(__file__).parents[1] / "alembic" / "versions"
LEGACY_AGENT_TOKEN_MIGRATION = MIGRATIONS / "20260723_0002_agent_tokens.py"
LEGACY_MIGRATION = MIGRATIONS / "20260723_0003_agent_oauth_clients.py"
COMPACT_MIGRATION = MIGRATIONS / "20260723_0004_compact_public_oauth.py"


def test_compact_oauth_migration_is_additive_and_has_three_tables() -> None:
    source = COMPACT_MIGRATION.read_text()

    assert 'down_revision = "20260723_0003"' in source
    assert source.count("op.create_table(") == 3
    assert '"oauth_clients"' in source
    assert '"oauth_grants"' in source
    assert '"oauth_credentials"' in source
    assert "client_secret" not in source
    assert "agent_tokens" not in source
    assert "op.drop_" not in source


def test_historical_oauth_migration_remains_present() -> None:
    assert LEGACY_AGENT_TOKEN_MIGRATION.exists()
    assert LEGACY_MIGRATION.exists()
