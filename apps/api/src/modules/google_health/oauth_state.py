from hashlib import sha256
from typing import Protocol

from redis.asyncio import Redis


class OAuthStateStore(Protocol):
    async def issue(self, state: str, user_id: int) -> None: ...

    async def consume(self, state: str) -> int | None: ...


class RedisOAuthStateStore:
    def __init__(self, redis_url: str, ttl_seconds: int = 600) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds

    async def issue(self, state: str, user_id: int) -> None:
        client = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            created = await client.set(
                self._key(state),
                str(user_id),
                ex=self.ttl_seconds,
                nx=True,
            )
            if not created:
                raise RuntimeError("OAuth state collision")
        finally:
            await client.aclose()

    async def consume(self, state: str) -> int | None:
        client = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            user_id = await client.getdel(self._key(state))
        finally:
            await client.aclose()
        return int(user_id) if user_id is not None else None

    @staticmethod
    def _key(state: str) -> str:
        digest = sha256(state.encode()).hexdigest()
        return f"lifestats:google-health:oauth-state:{digest}"
