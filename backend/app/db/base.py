import secrets
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def uuid7() -> UUID:
    """Create an RFC 9562 UUIDv7 without requiring Python 3.14."""
    timestamp_ms = time.time_ns() // 1_000_000
    random_bits = secrets.randbits(74)
    value = timestamp_ms << 80
    value |= 0x7 << 76
    value |= ((random_bits >> 62) & 0xFFF) << 64
    value |= 0b10 << 62
    value |= random_bits & ((1 << 62) - 1)
    return UUID(int=value)


class Base(DeclarativeBase):
    pass


class UUID7PrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
