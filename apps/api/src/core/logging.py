import json
import logging
import re
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FIELDS = (
    "event",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "user_id",
    "connection_id",
    "data_type",
    "trigger",
    "record_count",
    "status",
    "scope_count",
    "job_count",
    "event_id",
    "attempt",
    "delay_seconds",
    "upstream_status",
    "purged_count",
    "command",
)

_configured = False


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }
        for field in LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(app_env: str, log_level: str) -> None:
    global _configured
    level = getattr(logging, log_level.upper())
    if _configured:
        logging.getLogger().setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    if app_env == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
            )
        )
    logging.basicConfig(level=level, handlers=[handler], force=True)
    logging.captureWarnings(True)
    logging.getLogger("uvicorn.access").disabled = True
    _configured = True


def normalize_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def bind_request_id(value: str) -> Token[str]:
    return request_id_context.set(value)


def reset_request_id(token: Token[str]) -> None:
    request_id_context.reset(token)
