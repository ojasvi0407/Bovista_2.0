from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class Location(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"

    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    hierarchy_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "level IN ('COUNTRY', 'STATE', 'DISTRICT', 'BLOCK', 'VILLAGE')",
            name="ck_locations_level",
        ),
        Index("ix_locations_geometry_gist", "geometry", postgresql_using="gist"),
    )


class StaffGeographicAssignment(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_geographic_assignments"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_staff_one_active_assignment",
            "user_id",
            unique=True,
            postgresql_where=text("active = true"),
        ),
    )
