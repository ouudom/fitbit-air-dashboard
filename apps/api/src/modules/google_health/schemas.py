from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    days: int = Field(default=30, ge=1, le=365)
    data_types: list[str] | None = Field(default=None, alias="dataTypes", max_length=39)
    start_at: datetime | None = Field(default=None, alias="startAt")
    end_at: datetime | None = Field(default=None, alias="endAt")

    @model_validator(mode="after")
    def validate_range_and_types(self) -> "SyncRequest":
        if (self.start_at is None) != (self.end_at is None):
            raise ValueError("startAt and endAt must be provided together")
        if self.start_at is not None and self.end_at is not None:
            if self.start_at.utcoffset() is None or self.end_at.utcoffset() is None:
                raise ValueError("Sync range timestamps must include a UTC offset")
            if self.start_at >= self.end_at:
                raise ValueError("startAt must be before endAt")
            if self.end_at - self.start_at > timedelta(days=365):
                raise ValueError("Sync range cannot exceed 365 days")
            self.start_at = self.start_at.astimezone(UTC)
            self.end_at = self.end_at.astimezone(UTC)
        if self.data_types is not None:
            normalized = list(
                dict.fromkeys(item.strip() for item in self.data_types if item.strip())
            )
            if not normalized:
                raise ValueError("dataTypes cannot be empty")
            self.data_types = normalized
        return self
