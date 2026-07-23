import ast
from pathlib import Path

MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "20260723_0002_agent_tokens.py"


def _assignment(name: str) -> object:
    tree = ast.parse(MIGRATION.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Missing migration assignment: {name}")


def test_agent_tokens_migration_is_additive_and_follows_init() -> None:
    source = MIGRATION.read_text()
    assert _assignment("revision") == "20260723_0002"
    assert _assignment("down_revision") == "20260723_0001"
    assert 'op.create_table(\n        "agent_tokens"' in source
    assert "op.drop_" not in source
    assert "DROP " not in source.upper()
