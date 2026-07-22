import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "lifestats"
MODULES = {"identity", "google_health", "dashboard", "scoring", "timeline", "habits"}


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def test_domains_are_framework_independent() -> None:
    for module in MODULES:
        for path in (ROOT / module / "domain").glob("*.py"):
            assert not any(name.startswith(("fastapi", "sqlalchemy")) for name in imports(path)), (
                path
            )


def test_modules_do_not_import_another_modules_infrastructure() -> None:
    for module in MODULES:
        for path in (ROOT / module).rglob("*.py"):
            forbidden = {
                f"lifestats.{other}.infrastructure" for other in MODULES if other != module
            }
            assert not any(
                any(name.startswith(prefix) for prefix in forbidden) for name in imports(path)
            ), path
