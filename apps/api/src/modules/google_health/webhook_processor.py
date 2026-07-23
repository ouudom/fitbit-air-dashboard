from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.time import utc_now
from src.modules.google_health.models import (
    GoogleHealthConnection,
    GoogleHealthWebhookEvent,
)


async def process_webhook_event(db: AsyncSession, event_id: UUID) -> None:
    event = await db.scalar(
        select(GoogleHealthWebhookEvent)
        .where(GoogleHealthWebhookEvent.id == event_id)
        .with_for_update()
    )
    if event is None or event.status == "completed":
        return
    event.status = "running"
    event.error = None
    await db.commit()
    try:
        connection_id = event.connection_id
        if connection_id is None:
            connection_id = await db.scalar(
                select(GoogleHealthConnection.id).where(
                    GoogleHealthConnection.provider_user_id == event.provider_user_id
                )
            )
            event.connection_id = connection_id
        if connection_id is None:
            raise RuntimeError("No Google Health connection for webhook user")

        from src.modules.google_health.tasks import sync_google_health_type

        for data_type in event.data_type_ids:
            sync_google_health_type.delay(
                str(connection_id),
                data_type,
                "webhook",
                event.interval_start.isoformat() if event.interval_start else None,
                event.interval_end.isoformat() if event.interval_end else None,
            )
        event.status = "completed"
        event.processed_at = utc_now()
    except Exception as exc:
        event.status = "failed"
        event.error = str(exc)
        event.processed_at = utc_now()
        await db.commit()
        raise
    await db.commit()
