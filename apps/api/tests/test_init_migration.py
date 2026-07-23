import ast
from pathlib import Path

MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "20260723_0001_init.py"


def _tree() -> ast.Module:
    return ast.parse(MIGRATION.read_text())


def _assignment(name: str) -> object:
    for node in _tree().body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Missing migration assignment: {name}")


def _created_tables() -> set[str]:
    tables: set[str] = set()
    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
            and node.func.attr == "create_table"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            tables.add(node.args[0].value)
    return tables


def test_init_migration_is_the_root_revision() -> None:
    assert _assignment("revision") == "20260723_0001"
    assert _assignment("down_revision") is None


def test_init_migration_creates_only_current_tables() -> None:
    assert _created_tables() == {
        "users",
        "sessions",
        "gh_connections",
        "gh_sync_job",
        "gh_records",
        "gh_webhook_events",
    }


def test_init_migration_has_no_legacy_copy_or_destructive_sql() -> None:
    source = MIGRATION.read_text()
    forbidden = {
        "admin_accounts_v1",
        "app_sessions",
        "google_health_connections",
        "google_oauth_states",
        "INSERT INTO",
        "DROP TABLE",
    }
    upper_source = source.upper()
    assert not any(value.upper() in upper_source for value in forbidden)
    assert "op.execute" not in source
    assert "op.drop_" not in source
