from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class Vaccination(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vaccinations"

    animal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("animals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vaccine_name: Mapped[str] = mapped_column(String(160), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    administered_on: Mapped[date] = mapped_column(Date, nullable=False)
    next_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    administered_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "animal_id",
            "vaccine_name",
            "batch_number",
            "administered_on",
            name="uq_vaccination_dose",
        ),
        Index("ix_vaccinations_next_due", "next_due_on", "animal_id"),
    )
