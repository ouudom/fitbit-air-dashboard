import asyncio
import random
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.time import utc_now
from src.modules.google_health.crypto import TokenCipher
from src.modules.google_health.models import GoogleHealthConnection
from src.modules.google_health.registry import DataType, FetchMethod

MAX_REQUEST_ATTEMPTS = 5
MAX_RETRY_DELAY_SECONDS = 60.0


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
        self.cipher = TokenCipher(
            settings.token_encryption_key,
            settings.app_key,
            settings.google_client_secret,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def connection(self) -> GoogleHealthConnection:
        row = await self.db.scalar(
            select(GoogleHealthConnection).where(GoogleHealthConnection.user_id == self.user_id)
        )
        if row is None:
            raise RuntimeError("Google Health not connected")
        return row

    async def access_token(self, *, force_refresh: bool = False) -> str:
        connection = await self.connection()
        token = self.cipher.decrypt(connection.access_token_ciphertext)
        if (
            not force_refresh
            and token
            and connection.token_expires_at
            and connection.token_expires_at > utc_now() + timedelta(minutes=1)
        ):
            return token
        refresh = self.cipher.decrypt(connection.refresh_token_ciphertext)
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
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            connection.status = "expired"
            await self.db.commit()
            raise
        data = response.json()
        connection.access_token_ciphertext = self.cipher.encrypt(data["access_token"]) or ""
        connection.token_expires_at = utc_now() + timedelta(
            seconds=int(data.get("expires_in", 3600))
        )
        connection.status = "active"
        if data.get("refresh_token"):
            connection.refresh_token_ciphertext = self.cipher.encrypt(data["refresh_token"])
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
        refreshed = False
        for attempt in range(MAX_REQUEST_ATTEMPTS):
            try:
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
            except httpx.TransportError:
                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise
                await asyncio.sleep(_retry_delay(attempt))
                continue
            if response.status_code == 401 and not refreshed:
                await self.access_token(force_refresh=True)
                refreshed = True
                continue
            if response.status_code == 401:
                connection = await self.connection()
                connection.status = "expired"
                await self.db.commit()
            retryable = response.status_code in {408, 429} or response.status_code >= 500
            if retryable and attempt < MAX_REQUEST_ATTEMPTS - 1:
                await asyncio.sleep(_retry_delay(attempt, response))
                continue
            response.raise_for_status()
            return dict(response.json()) if response.content else {}
        raise RuntimeError("Google Health request failed")

    async def point_pages(
        self,
        data_type: DataType,
        start: date,
        end: date,
        *,
        page_token: str | None = None,
    ) -> AsyncIterator[tuple[list[dict[str, Any]], str | None]]:
        if data_type.fetch_method is FetchMethod.DAILY_ROLLUP:
            async for page in self._daily_rollup_pages(data_type, start, end, page_token):
                yield page
            return
        token = page_token
        suffix = ":reconcile" if data_type.fetch_method is FetchMethod.RECONCILE else ""
        while True:
            params: dict[str, Any] = {"pageSize": data_type.page_size}
            if data_type.filter_field:
                next_day = (end + timedelta(days=1)).isoformat()
                params["filter"] = (
                    f'{data_type.filter_field} >= "{start.isoformat()}" '
                    f'AND {data_type.filter_field} < "{next_day}"'
                )
            if token:
                params["pageToken"] = token
            data = await self.request(
                "GET",
                f"users/me/dataTypes/{data_type.endpoint_id}/dataPoints{suffix}",
                params=params,
            )
            points = _objects(data.get("dataPoints"))
            token = _page_token(data)
            yield points, token
            if token is None:
                return

    async def _daily_rollup_pages(
        self,
        data_type: DataType,
        start: date,
        end: date,
        page_token: str | None,
    ) -> AsyncIterator[tuple[list[dict[str, Any]], str | None]]:
        token = page_token
        while True:
            payload: dict[str, Any] = {
                "range": {
                    "start": {"date": _date_json(start), "time": {}},
                    "end": {
                        "date": _date_json(end + timedelta(days=1)),
                        "time": {},
                    },
                },
                "windowSizeDays": 1,
                "pageSize": data_type.page_size,
                "dataSourceFamily": "users/me/dataSourceFamilies/all-sources",
            }
            if token:
                payload["pageToken"] = token
            data = await self.request(
                "POST",
                f"users/me/dataTypes/{data_type.endpoint_id}/dataPoints:dailyRollUp",
                json=payload,
            )
            points = _objects(data.get("rollupDataPoints"))
            token = _page_token(data)
            yield points, token
            if token is None:
                return


def _date_json(value: date) -> dict[str, int]:
    return {"year": value.year, "month": value.month, "day": value.day}


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _page_token(data: dict[str, Any]) -> str | None:
    value = data.get("nextPageToken")
    return value if isinstance(value, str) and value else None


def _retry_delay(
    attempt: int,
    response: httpx.Response | None = None,
    *,
    uniform: Any = random.uniform,
) -> float:
    if response is not None and response.status_code == 429:
        retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
        if retry_after is not None:
            return retry_after
    ceiling = min(2**attempt, MAX_RETRY_DELAY_SECONDS)
    return float(uniform(0, ceiling))


def _retry_after_seconds(value: str | None, *, now: datetime | None = None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        current = now or datetime.now(UTC)
        return max(0.0, (retry_at.astimezone(UTC) - current).total_seconds())
