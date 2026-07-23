from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_scope


async def database_session() -> AsyncIterator[AsyncSession]:
    async for session in session_scope():
        yield session
