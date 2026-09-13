from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin, VersionMixin


class Farm(UUID7PrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "farms"

    owner_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_farms_geometry_gist", "geometry", postgresql_using="gist"),)


class Herd(UUID7PrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "herds"

    farm_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    species: Mapped[str] = mapped_column(String(40), nullable=False)
    animal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("animal_count >= 0", name="ck_herds_animal_count_nonnegative"),
    )


class Animal(UUID7PrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "animals"

    farm_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    herd_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("herds.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tag_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    species: Mapped[str] = mapped_column(String(40), nullable=False)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("farm_id", "tag_number", name="uq_animals_farm_tag"),
        Index(
            "ix_animals_active_farm",
            "farm_id",
            "created_at",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Disease(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diseases"

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("code", "revision", name="uq_disease_code_revision"),
        Index(
            "uq_active_disease_code",
            "code",
            unique=True,
            postgresql_where=text("active"),
        ),
    )


class Symptom(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "symptoms"

    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 5", name="ck_symptoms_severity"),
        UniqueConstraint("code", "revision", name="uq_symptom_code_revision"),
        Index(
            "uq_active_symptom_code",
            "code",
            unique=True,
            postgresql_where=text("active"),
        ),
    )


class DiseaseSymptom(Base):
    __tablename__ = "disease_symptoms"

    disease_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("diseases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symptom_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("symptoms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    default_weight: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)


class DiseaseReport(UUID7PrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "disease_reports"

    reporter_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    client_generated_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    farm_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("farms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    animal_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("animals.id", ondelete="RESTRICT"),
        nullable=True,
    )
    herd_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("herds.id", ondelete="RESTRICT"),
        nullable=True,
    )
    location_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    location_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    species: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mortality_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onset_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "reporter_id",
            "client_generated_id",
            name="uq_reports_reporter_client_id",
        ),
        CheckConstraint("affected_count >= 1", name="ck_reports_affected_positive"),
        CheckConstraint("mortality_count >= 0", name="ck_reports_mortality_nonnegative"),
        CheckConstraint(
            "mortality_count <= affected_count",
            name="ck_reports_mortality_not_above_affected",
        ),
        CheckConstraint("status IN ('DRAFT', 'SUBMITTED', 'AMENDED')", name="ck_reports_status"),
        Index("ix_reports_geometry_gist", "report_geometry", postgresql_using="gist"),
        Index("ix_reports_status_onset", "status", "onset_date"),
    )


class DiseaseReportSymptom(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "disease_report_symptoms"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symptom_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("symptoms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symptom_code_snapshot: Mapped[str] = mapped_column(String(60), nullable=False)
    severity_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportContextSnapshot(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "report_context_snapshots"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    vaccination: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    treatment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    environment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Attachment(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attachments"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    detected_mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_attachments_size_positive"),
        CheckConstraint(
            "scan_status IN ('PENDING', 'CLEAN', 'REJECTED')",
            name="ck_attachments_scan_status",
        ),
    )
