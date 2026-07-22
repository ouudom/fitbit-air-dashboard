from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.modules.google_health.client import GoogleHealthClient
from src.modules.google_health.sync import SyncService
from src.modules.habits.domain import HabitKind, RemoteLog


class GoogleHealthLogWriter:
    def __init__(self, db: AsyncSession, settings: Settings, user_id: int) -> None:
        self.db = db
        self.settings = settings
        self.user_id = user_id

    async def create(self, kind: HabitKind, value: float, occurred_at: datetime) -> RemoteLog:
        data_type, payload = self._payload(kind, value, occurred_at)
        client = GoogleHealthClient(self.db, self.settings, self.user_id)
        try:
            result = await client.request(
                "POST", f"users/me/dataTypes/{data_type}/dataPoints", json=payload
            )
            result = await client.wait_operation(result)
        finally:
            await client.close()
        response = result.get("response", result)
        source_name = response.get("name") if isinstance(response, dict) else None
        if not source_name:
            raise RuntimeError("Google Health write did not return a source name")
        await SyncService(self.db, self.settings, self.user_id).run(3, (data_type,))
        return RemoteLog(str(source_name), occurred_at, value)

    async def update(
        self, source_name: str, kind: HabitKind, value: float, occurred_at: datetime
    ) -> RemoteLog:
        data_type, payload = self._payload(kind, value, occurred_at)
        client = GoogleHealthClient(self.db, self.settings, self.user_id)
        try:
            mask = "hydrationLog.volume" if kind is HabitKind.GOOGLE_HYDRATION else "weight.weight"
            result = await client.request(
                "PATCH", source_name, json=payload, params={"updateMask": mask}
            )
            await client.wait_operation(result)
        finally:
            await client.close()
        await SyncService(self.db, self.settings, self.user_id).run(3, (data_type,))
        return RemoteLog(source_name, occurred_at, value)

    async def delete(self, source_name: str, kind: HabitKind) -> None:
        data_type, _ = self._payload(kind, 1, datetime.now().astimezone())
        client = GoogleHealthClient(self.db, self.settings, self.user_id)
        try:
            result = await client.request(
                "POST",
                f"users/me/dataTypes/{data_type}/dataPoints:batchDelete",
                json={"names": [source_name]},
            )
            await client.wait_operation(result)
        finally:
            await client.close()
        await SyncService(self.db, self.settings, self.user_id).run(3, (data_type,))

    def _payload(
        self, kind: HabitKind, value: float, occurred_at: datetime
    ) -> tuple[str, dict[str, Any]]:
        instant = occurred_at.isoformat()
        if kind is HabitKind.GOOGLE_HYDRATION:
            return "hydration-log", {
                "hydrationLog": {
                    "interval": {"startTime": instant, "endTime": instant},
                    "volume": {"milliliters": value},
                }
            }
        if kind is HabitKind.GOOGLE_WEIGHT:
            return "weight", {
                "weight": {
                    "sampleTime": {"physicalTime": instant},
                    "weight": {"kilograms": value},
                }
            }
        raise ValueError("Local habits cannot be sent to Google Health")
