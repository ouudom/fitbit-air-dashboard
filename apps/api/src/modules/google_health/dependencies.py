from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.dependencies import database_session
from src.modules.google_health.repository import GoogleHealthRepository
from src.modules.google_health.service import GoogleHealthService


def get_google_health_repository(
    db: Annotated[AsyncSession, Depends(database_session)],
) -> GoogleHealthRepository:
    return GoogleHealthRepository(db)


def get_google_health_service(
    db: Annotated[AsyncSession, Depends(database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleHealthService:
    return GoogleHealthService(db, settings)
