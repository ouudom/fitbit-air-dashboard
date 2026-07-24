from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.time import utc_now


class AgentScope(StrEnum):
    PROFILE_READ = "profile:read"
    TODAY_READ = "today:read"
    FITNESS_READ = "fitness:read"
    SLEEP_READ = "sleep:read"
    HEALTH_READ = "health:read"
    NUTRITION_READ = "nutrition:read"
    SYNC_READ = "sync:read"
    SYNC_WRITE = "sync:write"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_WRITE = "integration:write"
    ECG_READ = "ecg:read"
    IRN_READ = "irn:read"


class McpTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[AgentScope] = Field(min_length=1)
    expires_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Token name cannot be blank")
        return normalized

    @field_validator("scopes")
    @classmethod
    def unique_scopes(cls, value: list[AgentScope]) -> list[AgentScope]:
        return list(dict.fromkeys(value))

    @field_validator("expires_at")
    @classmethod
    def future_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Expiry must include a timezone")
            if value <= utc_now():
                raise ValueError("Expiry must be in the future")
        return value


class McpTokenResponse(BaseModel):
    id: UUID
    name: str
    token_prefix: str
    scopes: list[AgentScope]
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IssuedMcpTokenResponse(McpTokenResponse):
    token: str
    mcp_url: str
