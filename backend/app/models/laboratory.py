from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class LaboratorySample(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "laboratory_samples"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    specimen_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="REFERRED", nullable=False)
    lab_reference: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resulted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('REFERRED', 'COLLECTED', 'RECEIVED', 'PROCESSING', "
            "'RESULTED', 'REVIEWED')",
            name="ck_laboratory_samples_status",
        ),
        Index("ix_laboratory_samples_status_created", "status", "created_at"),
    )
