import base64
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from src import create_app
from src.core.config import Settings, get_settings
from src.modules.auth.dependencies import database_session
from src.modules.google_health.webhook_processor import process_webhook_event
from src.modules.google_health.webhooks import (
    GoogleHealthSignatureVerifier,
    GoogleHealthSubscriberClient,
    WebhookNotification,
    WebhookSignatureError,
    authorization_matches,
    is_verification_request,
)


def _varint(value: int) -> bytes:
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _field(number: int, value: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(value)) + value


@pytest.mark.asyncio
async def test_signature_verifier_uses_tink_prefix_and_rotating_keyset() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()
    key_id = 123456
    serialized_key = _field(3, numbers.x.to_bytes(32, "big")) + _field(
        4, numbers.y.to_bytes(32, "big")
    )
    keyset = {
        "key": [
            {
                "status": "ENABLED",
                "keyId": key_id,
                "keyData": {"value": base64.b64encode(serialized_key).decode()},
            }
        ]
    }
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=keyset)

    raw_body = b'{"data":{"healthUserId":"user-1"}}'
    der = private_key.sign(raw_body, ec.ECDSA(hashes.SHA256()))
    signature = b"\x01" + key_id.to_bytes(4, "big") + der
    verifier = GoogleHealthSignatureVerifier(
        "https://keys.example/keyset.json",
        transport=httpx.MockTransport(handler),
    )
    await verifier.verify(raw_body, base64.b64encode(signature).decode())
    await verifier.verify(raw_body, base64.b64encode(signature).decode())
    assert calls == 1
    await verifier.close()


@pytest.mark.asyncio
async def test_signature_verifier_rejects_modified_body() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    numbers = private_key.public_key().public_numbers()
    key_id = 7
    serialized_key = _field(3, numbers.x.to_bytes(32, "big")) + _field(
        4, numbers.y.to_bytes(32, "big")
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "key": [
                    {
                        "status": "ENABLED",
                        "keyId": key_id,
                        "keyData": {"value": base64.b64encode(serialized_key).decode()},
                    }
                ]
            },
        )

    signature = private_key.sign(b"original", ec.ECDSA(hashes.SHA256()))
    encoded = base64.b64encode(b"\x01" + key_id.to_bytes(4, "big") + signature).decode()
    verifier = GoogleHealthSignatureVerifier(
        "https://keys.example/keyset.json",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(WebhookSignatureError, match="Invalid webhook signature"):
        await verifier.verify(b"changed", encoded)
    await verifier.close()


def test_notification_parses_intervals_and_stable_hash() -> None:
    payload = {
        "data": {
            "version": "1",
            "clientProvidedSubscriptionName": "sub-1",
            "healthUserId": "health-user-1",
            "operation": "UPSERT",
            "dataType": "steps",
            "intervals": [
                {
                    "physicalTimeInterval": {
                        "startTime": "2026-03-08T01:29:00Z",
                        "endTime": "2026-03-08T01:34:00Z",
                    },
                    "civilDateTimeInterval": {
                        "startDateTime": {"date": {"year": 2026, "month": 3, "day": 7}},
                        "endDateTime": {"date": {"year": 2026, "month": 3, "day": 8}},
                    },
                }
            ],
        }
    }
    first = WebhookNotification.parse(json.dumps(payload).encode())
    second = WebhookNotification.parse(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    )
    assert first.event_hash == second.event_hash
    assert first.data_type == "steps"
    assert first.physical_interval[0].isoformat() == "2026-03-08T01:29:00+00:00"
    assert first.civil_interval[1].isoformat() == "2026-03-08"


def test_authorization_and_verification_request() -> None:
    assert authorization_matches("Bearer secret", "Bearer secret")
    assert not authorization_matches("Bearer wrong", "Bearer secret")
    assert is_verification_request(b'{"type":"verification"}')
    assert not is_verification_request(b'{"type":"notification"}')


@pytest.mark.asyncio
async def test_verification_handshake_requires_configured_authorization() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        google_health_webhook_enabled=True,
        google_health_webhook_auth_secret="Bearer webhook-secret",
    )
    app.dependency_overrides[database_session] = lambda: object()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        authorized = await client.post(
            "/api/v1/webhooks/google-health",
            content=b'{"type":"verification"}',
            headers={"Authorization": "Bearer webhook-secret"},
        )
        unauthorized = await client.post(
            "/api/v1/webhooks/google-health",
            content=b'{"type":"verification"}',
        )
    assert authorized.status_code == 200
    assert unauthorized.status_code == 401


@pytest.mark.asyncio
async def test_subscriber_apply_creates_then_can_inspect() -> None:
    requests: list[httpx.Request] = []
    created = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal created
        requests.append(request)
        if request.method == "GET" and not created:
            return httpx.Response(404)
        if request.method == "POST":
            created = True
        return httpx.Response(
            200,
            json={"name": "projects/123/subscribers/lifestats"},
        )

    client = GoogleHealthSubscriberClient(
        "https://health.googleapis.com/v4",
        "123",
        "lifestats",
        "access-token",
        transport=httpx.MockTransport(handler),
    )
    result = await client.apply(
        "https://example.com/api/v1/webhooks/google-health",
        "Bearer webhook-secret",
    )
    assert result["name"] == "projects/123/subscribers/lifestats"
    assert requests[1].url.params["subscriberId"] == "lifestats"
    body = json.loads(requests[1].content)
    assert body["subscriberConfigs"][0]["subscriptionCreatePolicy"] == "AUTOMATIC"
    assert "heart-rate" in body["subscriberConfigs"][0]["dataTypes"]
    await client.close()


@pytest.mark.asyncio
async def test_processor_dispatches_interval_sync_and_marks_event_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection_id = uuid4()
    event = SimpleNamespace(
        id=uuid4(),
        connection_id=connection_id,
        provider_user_id="health-user-1",
        data_type_ids=["steps"],
        interval_start=datetime(2026, 3, 8, 1, 29, tzinfo=UTC),
        interval_end=datetime(2026, 3, 8, 1, 34, tzinfo=UTC),
        status="queued",
        error=None,
        processed_at=None,
    )
    db = SimpleNamespace(scalar=AsyncMock(return_value=event), commit=AsyncMock())
    dispatched: list[tuple[object, ...]] = []

    from src.modules.google_health import tasks

    monkeypatch.setattr(
        tasks.sync_google_health_type,
        "delay",
        lambda *args: dispatched.append(args),
    )
    await process_webhook_event(db, event.id)
    assert dispatched == [
        (
            str(connection_id),
            "steps",
            "webhook",
            "2026-03-08T01:29:00+00:00",
            "2026-03-08T01:34:00+00:00",
        )
    ]
    assert event.status == "completed"
    assert event.processed_at is not None
