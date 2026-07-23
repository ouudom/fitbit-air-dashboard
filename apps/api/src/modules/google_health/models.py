import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class GoogleHealthConnection(Base):
    __tablename__ = "gh_connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    provider_user_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    access_token_ciphertext: Mapped[str] = mapped_column(Text)
    refresh_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Temporary compatibility properties for callers migrating from the v1 model.
    @property
    def health_user_id(self) -> str | None:
        return self.provider_user_id

    @health_user_id.setter
    def health_user_id(self, value: str | None) -> None:
        self.provider_user_id = value

    @property
    def access_token(self) -> str:
        return self.access_token_ciphertext

    @access_token.setter
    def access_token(self, value: str) -> None:
        self.access_token_ciphertext = value

    @property
    def refresh_token(self) -> str | None:
        return self.refresh_token_ciphertext

    @refresh_token.setter
    def refresh_token(self, value: str | None) -> None:
        self.refresh_token_ciphertext = value

    @property
    def expires_at(self) -> datetime | None:
        return self.token_expires_at

    @expires_at.setter
    def expires_at(self, value: datetime | None) -> None:
        self.token_expires_at = value

    @property
    def scope(self) -> str | None:
        return " ".join(self.scopes) if self.scopes else None

    @scope.setter
    def scope(self, value: str | None) -> None:
        self.scopes = value.split() if value else []


class GoogleHealthSyncJob(Base):
    __tablename__ = "gh_sync_job"
    __table_args__ = (
        Index("ix_gh_sync_job_enabled_next_poll_at", "enabled", "next_poll_at"),
        Index("ix_gh_sync_job_status_lease_until", "status", "lease_until"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gh_connections.id", ondelete="CASCADE"), primary_key=True
    )
    data_type: Mapped[str] = mapped_column(Text, primary_key=True)
    fetch_method: Mapped[str] = mapped_column(String(20), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    poll_interval_minutes: Mapped[int] = mapped_column(Integer)
    initial_lookback_days: Mapped[int] = mapped_column(Integer)
    incremental_overlap_minutes: Mapped[int] = mapped_column(Integer)
    page_size: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(SmallInteger, default=50, server_default="50")
    next_poll_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    range_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    range_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_page_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    record_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GoogleHealthRecord(Base):
    __tablename__ = "gh_records"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "data_type",
            "fetch_method",
            "identity_hash",
            name="uq_gh_records_identity",
        ),
        Index("ix_gh_records_connection_type_date", "connection_id", "data_type", "record_date"),
        Index(
            "ix_gh_records_connection_type_started",
            "connection_id",
            "data_type",
            "started_at",
        ),
        Index("ix_gh_records_provider_name", "provider_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gh_connections.id", ondelete="CASCADE")
    )
    data_type: Mapped[str] = mapped_column(Text)
    record_type: Mapped[str] = mapped_column(String(20))
    fetch_method: Mapped[str] = mapped_column(String(20))
    provider_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_hash: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    provider_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GhWebhookEvent(Base):
    __tablename__ = "gh_webhook_events"
    __table_args__ = (
        UniqueConstraint("event_hash", name="uq_gh_webhook_events_event_hash"),
        Index("ix_gh_webhook_events_status", "status"),
        Index("ix_gh_webhook_events_received_at", "received_at"),
        Index("ix_gh_webhook_events_provider_user_id", "provider_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("gh_connections.id", ondelete="SET NULL"), nullable=True
    )
    provider_user_id: Mapped[str] = mapped_column(Text)
    provider_subscription_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type_ids: Mapped[list[str]] = mapped_column(ARRAY(Text))
    operation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    interval_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interval_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    civil_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    civil_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    signature_verified: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
