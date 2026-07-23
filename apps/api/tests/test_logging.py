import json
import logging

import httpx
import pytest
from src.core.logging import (
    JsonFormatter,
    bind_request_id,
    normalize_request_id,
    reset_request_id,
)
from src.main import create_app


def test_json_formatter_adds_context_and_omits_unknown_sensitive_fields() -> None:
    token = bind_request_id("request-123")
    try:
        record = logging.LogRecord(
            "lifestats.test",
            logging.INFO,
            __file__,
            1,
            "Sync completed",
            (),
            None,
        )
        record.event = "sync_completed"
        record.data_type = "steps"
        record.access_token = "must-not-appear"
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "request-123"
    assert payload["event"] == "sync_completed"
    assert payload["data_type"] == "steps"
    assert "access_token" not in payload
    assert "must-not-appear" not in json.dumps(payload)


def test_request_id_accepts_safe_value_and_replaces_untrusted_value() -> None:
    assert normalize_request_id("proxy-request_123") == "proxy-request_123"
    generated = normalize_request_id("invalid request id\nforged-log")
    assert len(generated) == 32
    assert generated.isalnum()


@pytest.mark.asyncio
async def test_request_logging_returns_correlation_header() -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/healthz", headers={"X-Request-ID": "request-456"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-456"
