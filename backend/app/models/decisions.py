from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUID7PrimaryKeyMixin


class TriageRulePack(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "triage_rule_packs"

    version: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class RiskRulePack(UUID7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_rule_packs"

    version: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class TriageResult(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "triage_results"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_pack_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("triage_rule_packs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_pack_version: Mapped[str] = mapped_column(String(80), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    suspected_diseases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    contributing_factors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    missing_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    recommended_actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    data_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    disclaimer: Mapped[str] = mapped_column(String(240), nullable=False)
    invoked_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "disease_report_id",
            "snapshot_hash",
            "rule_pack_version",
            name="uq_triage_replay",
        ),
        CheckConstraint(
            "data_confidence BETWEEN 0 AND 1",
            name="ck_triage_confidence_range",
        ),
    )


class TriageFinding(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "triage_findings"

    triage_result_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("triage_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    disease_code: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_code: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 5), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "evidence_kind IN ('POSITIVE', 'NEGATIVE', 'MISSING')",
            name="ck_triage_findings_kind",
        ),
    )


class RiskScore(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "risk_scores"

    disease_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("disease_reports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_pack_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("risk_rule_packs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_pack_version: Mapped[str] = mapped_column(String(80), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    data_confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    missing_signals: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    invoked_by_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "disease_report_id",
            "snapshot_hash",
            "rule_pack_version",
            name="uq_risk_replay",
        ),
        CheckConstraint("value BETWEEN 0 AND 100", name="ck_risk_value_range"),
        CheckConstraint(
            "category IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_risk_category",
        ),
        CheckConstraint(
            "data_confidence BETWEEN 0 AND 1",
            name="ck_risk_confidence_range",
        ),
        Index("ix_risk_category_created", "category", "created_at"),
    )


class RiskFactorContribution(UUID7PrimaryKeyMixin, Base):
    __tablename__ = "risk_factor_contributions"

    risk_score_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("risk_scores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    factor: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_value: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "normalized_value BETWEEN 0 AND 1",
            name="ck_risk_factor_normalized_range",
        ),
        CheckConstraint("weight BETWEEN 0 AND 1", name="ck_risk_factor_weight_range"),
    )
