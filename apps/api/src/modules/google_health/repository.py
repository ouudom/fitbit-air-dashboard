from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.google_health.models import (
    GoogleHealthConnection,
    GoogleHealthSyncJob,
    GoogleHealthWebhookEvent,
)
from src.modules.google_health.webhooks import WebhookNotification


class GoogleHealthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def connection_for_user(
        self,
        user_id: int,
        *,
        active_only: bool = False,
    ) -> GoogleHealthConnection | None:
        query = select(GoogleHealthConnection).where(GoogleHealthConnection.user_id == user_id)
        if active_only:
            query = query.where(GoogleHealthConnection.status == "active")
        return cast(GoogleHealthConnection | None, await self.db.scalar(query))

    async def jobs_for_connection(
        self,
        connection_id: UUID,
    ) -> list[GoogleHealthSyncJob]:
        return list(
            (
                await self.db.scalars(
                    select(GoogleHealthSyncJob)
                    .where(GoogleHealthSyncJob.connection_id == connection_id)
                    .order_by(GoogleHealthSyncJob.priority, GoogleHealthSyncJob.data_type)
                )
            ).all()
        )

    async def store_webhook_event(
        self,
        notification: WebhookNotification,
    ) -> UUID | None:
        connection_id = await self.db.scalar(
            select(GoogleHealthConnection.id).where(
                GoogleHealthConnection.provider_user_id == notification.provider_user_id
            )
        )
        interval_start, interval_end = notification.physical_interval
        civil_start, civil_end = notification.civil_interval
        statement = (
            insert(GoogleHealthWebhookEvent)
            .values(
                connection_id=connection_id,
                provider_user_id=notification.provider_user_id,
                provider_subscription_name=notification.subscription_name,
                data_type_ids=[notification.data_type],
                operation=notification.operation,
                interval_start=interval_start,
                interval_end=interval_end,
                civil_start_date=civil_start,
                civil_end_date=civil_end,
                event_hash=notification.event_hash,
                raw_payload=notification.raw_payload,
                signature_verified=True,
                status="queued",
            )
            .on_conflict_do_nothing(index_elements=["event_hash"])
            .returning(GoogleHealthWebhookEvent.id)
        )
        event_id = (await self.db.execute(statement)).scalar_one_or_none()
        await self.db.commit()
        if event_id is not None:
            return event_id

        duplicate = (
            await self.db.execute(
                select(
                    GoogleHealthWebhookEvent.id,
                    GoogleHealthWebhookEvent.status,
                ).where(GoogleHealthWebhookEvent.event_hash == notification.event_hash)
            )
        ).one()
        if duplicate.status in {"queued", "failed"}:
            return cast(UUID, duplicate.id)
        return None
