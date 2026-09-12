from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin

ROLE_CODES = (
    "FARMER",
    "PARAVET",
    "VETERINARIAN",
    "LAB_TECHNICIAN",
    "DISTRICT_OFFICER",
    "ADMIN",
)


class User(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    user_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mobile_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    staff_identifier: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("user_type IN ('FARMER', 'STAFF')", name="ck_users_type"),
        CheckConstraint(
            "(user_type = 'FARMER' AND mobile_number IS NOT NULL) OR "
            "(user_type = 'STAFF' AND staff_identifier IS NOT NULL)",
            name="ck_users_identity",
        ),
    )


class Role(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "code IN ('FARMER', 'PARAVET', 'VETERINARIAN', 'LAB_TECHNICIAN', "
            "'DISTRICT_OFFICER', 'ADMIN')",
            name="ck_roles_code",
        ),
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class AuthIdentity(TimestampMixin, Base):
    __tablename__ = "auth_identities"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MfaCredential(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mfa_credentials"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    totp_secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    recovery_code_hashes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MfaChallenge(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mfa_challenges"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshSession(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refresh_sessions"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    device_id: Mapped[str] = mapped_column(String(160), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reuse_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CaseReviewGrant(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_review_grants"

    grantee_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    granted_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "grantee_id",
            "disease_report_id",
            "expires_at",
            name="uq_case_review_grant_window",
        ),
    )
