from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin, utc_now


class Treatment(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treatments"
    animal_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="RESTRICT"), index=True
    )
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("veterinary_cases.id", ondelete="RESTRICT"), index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(160))
    dosage: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    dosage_unit: Mapped[str] = mapped_column(String(40))
    duration_days: Mapped[int] = mapped_column(Integer)
    administered_on: Mapped[date] = mapped_column(Date)
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        CheckConstraint("dosage > 0 AND duration_days > 0", name="ck_treatment_positive"),
    )


class ClinicalReversal(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "clinical_reversals"
    vaccination_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("vaccinations.id", ondelete="RESTRICT"), unique=True
    )
    treatment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("treatments.id", ondelete="RESTRICT"), unique=True
    )
    reason: Mapped[str] = mapped_column(String(1000))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        CheckConstraint(
            "(vaccination_id IS NULL) <> (treatment_id IS NULL)", name="ck_reversal_target"
        ),
    )


class LaboratoryResult(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "laboratory_results"
    sample_id: Mapped[UUID] = mapped_column(
        ForeignKey("laboratory_samples.id", ondelete="RESTRICT"), unique=True
    )
    disease_code: Mapped[str] = mapped_column(String(60))
    outcome: Mapped[str] = mapped_column(String(24))
    findings: Mapped[str] = mapped_column(String(4000))
    published_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('POSITIVE', 'NEGATIVE', 'INCONCLUSIVE')", name="ck_lab_outcome"
        ),
    )


class LaboratoryTransition(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "laboratory_transitions"
    sample_id: Mapped[UUID] = mapped_column(
        ForeignKey("laboratory_samples.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    from_state: Mapped[str] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(1000))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CaseTransition(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "case_transitions"
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("veterinary_cases.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    from_state: Mapped[str] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(1000))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
