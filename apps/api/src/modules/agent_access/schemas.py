from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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


class AgentOAuthGrantResponse(BaseModel):
    id: UUID
    client_id: str
    client_name: str
    scopes: list[AgentScope]
    resource: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class OAuthAuthorizationPreviewResponse(BaseModel):
    client_id: str
    client_name: str
    redirect_uri: str
    scopes: list[AgentScope]
    resource: str


class OAuthAuthorizationDecisionRequest(BaseModel):
    approved: bool
    client_id: str
    redirect_uri: str
    response_type: Literal["code"]
    code_challenge: str
    code_challenge_method: Literal["S256"]
    scope: str
    resource: str
    state: str | None = None


class OAuthAuthorizationDecisionResponse(BaseModel):
    redirect_to: str
