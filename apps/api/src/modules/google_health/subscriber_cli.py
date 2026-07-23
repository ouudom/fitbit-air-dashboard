import argparse
import asyncio
import json
from collections.abc import Sequence

import google.auth
from google.auth.transport.requests import Request

from src.core.config import get_settings
from src.modules.google_health.webhooks import GoogleHealthSubscriberClient

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def run(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="google-health-subscriber")
    parser.add_argument("command", choices=("apply", "inspect"))
    arguments = parser.parse_args(argv)
    asyncio.run(_run(arguments.command))


async def _run(command: str) -> None:
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("GOOGLE_CLOUD_PROJECT_NUMBER", settings.google_cloud_project_number),
            ("GOOGLE_HEALTH_SUBSCRIBER_ID", settings.google_health_subscriber_id),
        )
        if not value
    ]
    if command == "apply":
        missing.extend(
            name
            for name, value in (
                ("GOOGLE_HEALTH_WEBHOOK_URL", settings.google_health_webhook_url),
                (
                    "GOOGLE_HEALTH_WEBHOOK_AUTH_SECRET",
                    settings.google_health_webhook_auth_secret,
                ),
            )
            if not value
        )
    if missing:
        raise SystemExit(f"Missing configuration: {', '.join(missing)}")

    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    credentials.refresh(Request())  # type: ignore[no-untyped-call]
    if not credentials.token:
        raise SystemExit("Application Default Credentials returned no access token")
    client = GoogleHealthSubscriberClient(
        settings.google_health_url,
        settings.google_cloud_project_number,
        settings.google_health_subscriber_id,
        credentials.token,
    )
    try:
        result: dict[str, object] | None
        if command == "apply":
            result = await client.apply(
                settings.google_health_webhook_url,
                settings.google_health_webhook_auth_secret,
            )
        else:
            result = await client.inspect()
        print("not found" if result is None else json.dumps(result, indent=2, sort_keys=True))
    finally:
        await client.close()
