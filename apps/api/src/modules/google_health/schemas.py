from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
