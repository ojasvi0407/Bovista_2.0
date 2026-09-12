from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class AuditLog(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (Index("ix_audit_resource", "resource_type", "resource_id"),)


class OutboxEvent(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_events"

    topic: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_outbox_pending", "published_at", "created_at"),)


class IdempotencyReceipt(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_receipts"

    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("actor_id", "idempotency_key", name="uq_idempotency_actor_key"),
    )
