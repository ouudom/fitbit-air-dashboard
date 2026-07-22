import asyncio
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lifestats.google_health.infrastructure.crypto import TokenCipher
from lifestats.google_health.infrastructure.models import GoogleHealthConnection
from lifestats.shared_kernel.domain.time import utc_now
from lifestats.shared_kernel.infrastructure.config import Settings


class GoogleHealthClient:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        user_id: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.user_id = user_id
        self.http = httpx.AsyncClient(timeout=30, transport=transport)
        self.cipher = TokenCipher(settings.token_encryption_key, settings.app_key)

    async def close(self) -> None:
        await self.http.aclose()

    async def connection(self) -> GoogleHealthConnection:
        row = await self.db.scalar(
            select(GoogleHealthConnection).where(GoogleHealthConnection.user_id == self.user_id)
        )
        if row is None:
            raise RuntimeError("Google Health not connected")
        return row

    async def access_token(self) -> str:
        connection = await self.connection()
        token = self.cipher.decrypt(connection.access_token)
        if (
            token
            and connection.expires_at
            and connection.expires_at > utc_now() + timedelta(minutes=1)
        ):
            return token
        refresh = self.cipher.decrypt(connection.refresh_token)
        if not refresh:
            raise RuntimeError("Google Health authorization expired")
        response = await self.http.post(
            self.settings.google_token_url,
            data={
                "refresh_token": refresh,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
        connection.access_token = self.cipher.encrypt(data["access_token"]) or ""
        connection.expires_at = utc_now() + timedelta(seconds=int(data.get("expires_in", 3600)))
        if data.get("refresh_token"):
            connection.refresh_token = self.cipher.encrypt(data["refresh_token"])
        await self.db.commit()
        return str(data["access_token"])

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.google_health_url.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(4):
            response = await self.http.request(
                method,
                url,
                json=json,
                params=params,
                headers={
                    "Authorization": f"Bearer {await self.access_token()}",
                    "Accept": "application/json",
                },
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 3:
                    await asyncio.sleep(2**attempt)
                    continue
            response.raise_for_status()
            return dict(response.json()) if response.content else {}
        raise RuntimeError("Google Health request failed")

    async def reconcile_points(
        self, data_type: str, start: date, end: date
    ) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        page: str | None = None
        snake = data_type.replace("-", "_")
        if data_type.startswith("daily-"):
            field = f"{snake}.date"
        elif data_type == "sleep":
            field = "sleep.interval.civil_end_time"
        elif data_type in {"exercise", "active-minutes", "hydration-log"}:
            field = f"{snake}.interval.civil_start_time"
        else:
            field = f"{snake}.sample_time.civil_time"
        while True:
            next_day = (end + timedelta(days=1)).isoformat()
            params: dict[str, Any] = {
                "pageSize": 25 if data_type in {"sleep", "exercise"} else 1000,
                "filter": f'{field} >= "{start.isoformat()}" AND {field} < "{next_day}"',
            }
            if page:
                params["pageToken"] = page
            data = await self.request(
                "GET",
                f"users/me/dataTypes/{data_type}/dataPoints:reconcile",
                params=params,
            )
            points.extend(data.get("dataPoints", []))
            page = data.get("nextPageToken")
            if not page:
                return points

    async def daily_rollup(self, data_type: str, start: date, end: date) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=13), end)
            payload = {
                "range": {
                    "start": {"date": _date_json(cursor), "time": {}},
                    "end": {
                        "date": _date_json(chunk_end),
                        "time": {"hours": 23, "minutes": 59, "seconds": 59},
                    },
                },
                "windowSizeDays": 1,
            }
            data = await self.request(
                "POST",
                f"users/me/dataTypes/{data_type}/dataPoints:dailyRollUp",
                json=payload,
            )
            points.extend(data.get("rollupDataPoints", []))
            cursor = chunk_end + timedelta(days=1)
        return points

    async def wait_operation(self, operation: dict[str, Any]) -> dict[str, Any]:
        current = operation
        for attempt in range(8):
            if not current.get("name") or current.get("done"):
                return current
            await asyncio.sleep(min(0.5 * 2**attempt, 4))
            current = await self.request("GET", str(current["name"]))
        raise RuntimeError("Google Health write timed out")


def _date_json(value: date) -> dict[str, int]:
    return {"year": value.year, "month": value.month, "day": value.day}
