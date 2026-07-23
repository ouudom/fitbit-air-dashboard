import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from src.core.time import utc_now
from src.modules.google_health.registry import WEBHOOK_DATA_TYPE_IDS

SIGNATURE_HEADER = "GOOGLE-HEALTH-API-SIGNATURE"


class WebhookSignatureError(ValueError):
    pass


@dataclass(frozen=True)
class WebhookNotification:
    provider_user_id: str
    subscription_name: str | None
    data_type: str
    operation: str
    intervals: list[dict[str, Any]]
    raw_payload: dict[str, Any]
    event_hash: str

    @classmethod
    def parse(cls, raw_body: bytes) -> "WebhookNotification":
        try:
            payload = json.loads(raw_body)
            data = payload["data"]
            provider_user_id = str(data["healthUserId"])
            data_type = str(data["dataType"])
            operation = str(data["operation"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid Google Health webhook payload") from exc
        if not provider_user_id or not data_type or operation not in {"UPSERT", "DELETE"}:
            raise ValueError("Invalid Google Health webhook payload")
        intervals = data.get("intervals", [])
        if not isinstance(intervals, list):
            raise ValueError("Invalid Google Health webhook intervals")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return cls(
            provider_user_id=provider_user_id,
            subscription_name=data.get("clientProvidedSubscriptionName"),
            data_type=data_type,
            operation=operation,
            intervals=intervals,
            raw_payload=payload,
            event_hash=hashlib.sha256(canonical).hexdigest(),
        )

    @property
    def physical_interval(self) -> tuple[datetime | None, datetime | None]:
        starts: list[datetime] = []
        ends: list[datetime] = []
        for interval in self.intervals:
            physical = interval.get("physicalTimeInterval", {})
            if physical.get("startTime"):
                starts.append(_parse_datetime(str(physical["startTime"])))
            if physical.get("endTime"):
                ends.append(_parse_datetime(str(physical["endTime"])))
        return (min(starts) if starts else None, max(ends) if ends else None)

    @property
    def civil_interval(self) -> tuple[date | None, date | None]:
        starts: list[date] = []
        ends: list[date] = []
        for interval in self.intervals:
            civil = interval.get("civilDateTimeInterval", {})
            if civil.get("startDateTime", {}).get("date"):
                starts.append(_parse_date(civil["startDateTime"]["date"]))
            if civil.get("endDateTime", {}).get("date"):
                ends.append(_parse_date(civil["endDateTime"]["date"]))
        return (min(starts) if starts else None, max(ends) if ends else None)


class GoogleHealthSignatureVerifier:
    def __init__(
        self,
        keyset_url: str,
        *,
        ttl_seconds: int = 3600,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.keyset_url = keyset_url
        self.ttl_seconds = ttl_seconds
        self.http = httpx.AsyncClient(timeout=10, transport=transport)
        self._keys: dict[int, ec.EllipticCurvePublicKey] = {}
        self._expires_at: datetime | None = None

    async def close(self) -> None:
        await self.http.aclose()

    async def verify(self, raw_body: bytes, encoded_signature: str) -> None:
        try:
            signature = base64.b64decode(encoded_signature, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise WebhookSignatureError("Invalid webhook signature encoding") from exc
        if len(signature) <= 5 or signature[0] != 1:
            raise WebhookSignatureError("Invalid webhook signature prefix")
        key_id = int.from_bytes(signature[1:5], "big")
        key = (await self._public_keys()).get(key_id)
        if key is None:
            await self._refresh_keys()
            key = self._keys.get(key_id)
        if key is None:
            raise WebhookSignatureError("Unknown webhook signing key")
        try:
            key.verify(signature[5:], raw_body, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as exc:
            raise WebhookSignatureError("Invalid webhook signature") from exc

    async def _public_keys(self) -> dict[int, ec.EllipticCurvePublicKey]:
        if self._expires_at is None or utc_now() >= self._expires_at:
            await self._refresh_keys()
        return self._keys

    async def _refresh_keys(self) -> None:
        response = await self.http.get(self.keyset_url)
        response.raise_for_status()
        keyset = response.json()
        keys: dict[int, ec.EllipticCurvePublicKey] = {}
        for item in keyset.get("key", []):
            if item.get("status") != "ENABLED":
                continue
            key_id = int(item["keyId"])
            serialized = base64.b64decode(item["keyData"]["value"])
            x, y = _parse_ecdsa_public_key(serialized)
            keys[key_id] = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        if not keys:
            raise WebhookSignatureError("Webhook public keyset is empty")
        self._keys = keys
        self._expires_at = utc_now() + timedelta(seconds=self.ttl_seconds)


def authorization_matches(actual: str | None, expected: str) -> bool:
    return bool(actual and expected and hmac.compare_digest(actual, expected))


def is_verification_request(raw_body: bytes) -> bool:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return False
    return bool(payload == {"type": "verification"})


def _parse_ecdsa_public_key(payload: bytes) -> tuple[int, int]:
    fields = _protobuf_fields(payload)
    try:
        return int.from_bytes(fields[3], "big"), int.from_bytes(fields[4], "big")
    except KeyError as exc:
        raise WebhookSignatureError("Invalid ECDSA public key") from exc


def _protobuf_fields(payload: bytes) -> dict[int, bytes]:
    fields: dict[int, bytes] = {}
    position = 0
    while position < len(payload):
        tag, position = _read_varint(payload, position)
        field_number = tag >> 3
        wire_type = tag & 7
        if wire_type == 0:
            _, position = _read_varint(payload, position)
        elif wire_type == 2:
            length, position = _read_varint(payload, position)
            end = position + length
            if end > len(payload):
                raise WebhookSignatureError("Invalid protobuf key")
            fields[field_number] = payload[position:end]
            position = end
        elif wire_type == 5:
            position += 4
        elif wire_type == 1:
            position += 8
        else:
            raise WebhookSignatureError("Unsupported protobuf key")
        if position > len(payload):
            raise WebhookSignatureError("Invalid protobuf key")
    return fields


def _read_varint(payload: bytes, position: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while position < len(payload) and shift < 64:
        byte = payload[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7
    raise WebhookSignatureError("Invalid protobuf varint")


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_date(value: dict[str, Any]) -> date:
    return date(int(value["year"]), int(value["month"]), int(value["day"]))


class GoogleHealthSubscriberClient:
    def __init__(
        self,
        api_url: str,
        project_number: str,
        subscriber_id: str,
        access_token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.project_number = project_number
        self.subscriber_id = subscriber_id
        self.http = httpx.AsyncClient(
            timeout=30,
            transport=transport,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )

    @property
    def resource_path(self) -> str:
        return f"projects/{self.project_number}/subscribers/{self.subscriber_id}"

    async def close(self) -> None:
        await self.http.aclose()

    async def inspect(self) -> dict[str, Any] | None:
        response = await self.http.get(f"{self.api_url}/{self.resource_path}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return dict(response.json())

    async def apply(self, endpoint_uri: str, authorization_secret: str) -> dict[str, Any]:
        body = {
            "endpointUri": endpoint_uri,
            "subscriberConfigs": [
                {
                    "dataTypes": list(WEBHOOK_DATA_TYPE_IDS),
                    "subscriptionCreatePolicy": "AUTOMATIC",
                }
            ],
            "endpointAuthorization": {"secret": authorization_secret},
        }
        current = await self.inspect()
        if current is None:
            response = await self.http.post(
                f"{self.api_url}/projects/{self.project_number}/subscribers",
                params={"subscriberId": self.subscriber_id},
                json=body,
            )
        else:
            response = await self.http.patch(
                f"{self.api_url}/{self.resource_path}",
                params={"updateMask": ("endpointUri,subscriberConfigs,endpointAuthorization")},
                json=body,
            )
        response.raise_for_status()
        applied = await self.inspect()
        if applied is None:
            raise RuntimeError("Google Health subscriber missing after apply")
        return applied
