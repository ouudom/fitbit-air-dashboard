import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from src.modules.google_health import tasks


def test_task_runner_disposes_engine_in_each_task_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_loops: list[asyncio.AbstractEventLoop] = []
    dispose_loops: list[asyncio.AbstractEventLoop] = []

    async def operation() -> str:
        task_loops.append(asyncio.get_running_loop())
        return "completed"

    async def dispose() -> None:
        dispose_loops.append(asyncio.get_running_loop())

    monkeypatch.setattr(tasks, "engine", SimpleNamespace(dispose=dispose))

    assert tasks._run_async_task(operation()) == "completed"
    assert tasks._run_async_task(operation()) == "completed"
    assert task_loops == dispose_loops
    assert task_loops[0] is not task_loops[1]


def test_task_runner_disposes_engine_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispose = AsyncMock()
    monkeypatch.setattr(tasks, "engine", SimpleNamespace(dispose=dispose))

    async def operation() -> None:
        raise RuntimeError("sync failed")

    with pytest.raises(RuntimeError, match="sync failed"):
        tasks._run_async_task(operation())

    dispose.assert_awaited_once()
