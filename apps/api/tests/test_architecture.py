import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src" / "modules"
CORE = Path(__file__).parents[1] / "src" / "core"
MODULES = {"auth", "google_health", "dashboard", "timeline"}


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
        for path in (ROOT / module).glob("domain.py"):
            assert not any(name.startswith(("fastapi", "sqlalchemy")) for name in imports(path)), (
                path
            )


def test_http_framework_stays_in_routers() -> None:
    for module in MODULES:
        for path in (ROOT / module).glob("*.py"):
            if path.name not in {"router.py", "dependencies.py"}:
                assert not any(name.startswith("fastapi") for name in imports(path)), path


def test_repositories_are_http_framework_independent() -> None:
    for module in MODULES:
        for path in (ROOT / module).glob("repository.py"):
            assert not any(name.startswith("fastapi") for name in imports(path)), path


def test_core_does_not_import_modules() -> None:
    for path in CORE.glob("*.py"):
        assert not any(name.startswith("src.modules") for name in imports(path)), path
