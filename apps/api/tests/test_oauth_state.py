import pytest
from src.modules.google_health.oauth_state import RedisOAuthStateStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.closed = 0

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int,
        nx: bool,
    ) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.ttls[key] = ex
        return True

    async def getdel(self, key: str) -> str | None:
        self.ttls.pop(key, None)
        return self.values.pop(key, None)

    async def aclose(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_oauth_state_is_hashed_expiring_and_single_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeRedis()
    monkeypatch.setattr(
        "src.modules.google_health.oauth_state.Redis.from_url",
        lambda *_args, **_kwargs: fake,
    )
    store = RedisOAuthStateStore("redis://unused", ttl_seconds=600)

    await store.issue("secret-state", 42)

    [key] = fake.values
    assert "secret-state" not in key
    assert fake.values[key] == "42"
    assert fake.ttls[key] == 600
    assert await store.consume("secret-state") == 42
    assert await store.consume("secret-state") is None
    assert fake.closed == 3
