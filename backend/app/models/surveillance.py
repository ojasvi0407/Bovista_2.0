from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class VeterinaryCase(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "veterinary_cases"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_veterinarian_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), default="OPEN", nullable=False)
    escalation_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'REFERRED', 'CLOSED')",
            name="ck_veterinary_cases_status",
        ),
        Index(
            "uq_open_case_per_report",
            "disease_report_id",
            unique=True,
            postgresql_where=text("status <> 'CLOSED'"),
        ),
    )


class Alert(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    risk_score_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("risk_scores.id", ondelete="RESTRICT"),
        nullable=True,
    )
    recipient_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_alerts_severity",
        ),
        CheckConstraint("status IN ('ACTIVE', 'ACKNOWLEDGED', 'CLOSED')", name="ck_alerts_status"),
        Index(
            "uq_active_risk_alert",
            "disease_report_id",
            "alert_type",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_alerts_recipient_status_created", "recipient_id", "status", "created_at"),
    )


class Outbreak(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbreaks"

    location_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    disease_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(20), default="POTENTIAL", nullable=False)
    config_version: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    cluster_geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )
    declared_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    declared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "state IN ('POTENTIAL', 'DECLARED', 'DISMISSED', 'CLOSED')",
            name="ck_outbreaks_state",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_outbreaks_score_range"),
        Index("ix_outbreak_geometry_gist", "cluster_geometry", postgresql_using="gist"),
        Index("ix_outbreak_state_created", "state", "created_at"),
        Index(
            "uq_active_potential_outbreak",
            "location_id",
            "disease_code",
            "config_version",
            unique=True,
            postgresql_where=text("state = 'POTENTIAL'"),
        ),
    )


class OutbreakReportMembership(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "outbreak_report_memberships"

    outbreak_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("outbreaks.id", ondelete="CASCADE"),
        nullable=False,
    )
    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    distance_km: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    included_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "outbreak_id",
            "disease_report_id",
            name="uq_outbreak_report_membership",
        ),
        CheckConstraint("distance_km >= 0", name="ck_outbreak_distance_nonnegative"),
    )


class OutbreakTransition(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "outbreak_transitions"

    outbreak_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("outbreaks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_state: Mapped[str] = mapped_column(String(20), nullable=False)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
