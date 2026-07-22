import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("LIFESTATS_INTEGRATION_DATABASE_URL"),
    reason="isolated PostgreSQL integration database not configured",
)


@pytest.mark.asyncio
async def test_setup_session_and_empty_dashboard() -> None:
    from lifestats.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        setup = await client.post(
            "/api/v1/setup",
            json={
                "setup_token": "integration-setup-token",
                "email": "admin@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert setup.status_code == 201, setup.text
        assert setup.cookies.get("lifestats_session")

        session = await client.get("/api/v1/session")
        assert session.status_code == 200
        assert session.json()["user"]["email"] == "admin@example.com"

        dashboard = await client.get("/api/v1/dashboard?date=2026-07-22")
        assert dashboard.status_code == 200, dashboard.text
        payload = dashboard.json()
        assert payload["timezone"] == "Asia/Phnom_Penh"
        assert [score["label"] for score in payload["scores"]] == [
            "LifeStats Readiness",
            "LifeStats Stress",
            "LifeStats Energy",
        ]
        assert all(score["value"] is None for score in payload["scores"])

        repeat_setup = await client.post(
            "/api/v1/setup",
            json={
                "setup_token": "integration-setup-token",
                "email": "other@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert repeat_setup.status_code == 404
