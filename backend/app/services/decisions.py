import hashlib
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.decisions import (
    RiskFactorContribution,
    RiskRulePack,
    RiskScore,
    TriageFinding,
    TriageResult,
    TriageRulePack,
)
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import Role, User, UserRole
from app.models.reports import DiseaseReport, DiseaseReportSymptom, ReportContextSnapshot
from app.models.surveillance import Alert, OutbreakReportMembership, VeterinaryCase
from app.risk.contracts import DiseaseRule, ReportSnapshot, TriageRuleSet
from app.risk.scoring import RiskFactor, RiskScorer
from app.risk.triage import RuleBasedTriageProvider
from app.services.auth import CurrentPrincipal
from app.services.authorization import authorize
from app.services.reports import InvalidReportError, ReportNotFoundError
from app.services.trust import claim_idempotency, enqueue_event, record_audit


class DecisionConfigurationError(Exception):
    pass


class DecisionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _submitted_report(self, report_id: UUID) -> DiseaseReport:
        report = await self.session.scalar(
            select(DiseaseReport).where(DiseaseReport.id == report_id).with_for_update()
        )
        if report is None:
            raise ReportNotFoundError("Report not found.")
        if report.status != "SUBMITTED" or report.snapshot_hash is None:
            raise InvalidReportError("Only a submitted report can be evaluated.")
        return report

    async def _snapshot(self, report: DiseaseReport) -> ReportSnapshot:
        symptom_codes = tuple(
            (
                await self.session.scalars(
                    select(DiseaseReportSymptom.symptom_code_snapshot).where(
                        DiseaseReportSymptom.disease_report_id == report.id
                    )
                )
            ).all()
        )
        context = await self.session.scalar(
            select(ReportContextSnapshot).where(
                ReportContextSnapshot.disease_report_id == report.id
            )
        )
        signals: dict[str, bool | str | int | float | None] = {
            code.casefold(): True for code in symptom_codes
        }
        vaccination = context.vaccination if context else None
        signals["vaccination_status"] = vaccination.get("status") if vaccination else None
        signals["vaccinated_recently"] = bool(
            vaccination and vaccination.get("vaccinated_recently")
        )
        return ReportSnapshot(report.snapshot_hash, signals)

    async def _risk_signals(self, report: DiseaseReport) -> dict[str, Decimal | None]:
        severities = (
            await self.session.scalars(
                select(DiseaseReportSymptom.severity_snapshot).where(
                    DiseaseReportSymptom.disease_report_id == report.id
                )
            )
        ).all()
        context = await self.session.scalar(
            select(ReportContextSnapshot).where(
                ReportContextSnapshot.disease_report_id == report.id
            )
        )
        vaccination = context.vaccination if context else None
        environment = context.environment if context else None
        status = vaccination.get("status") if vaccination else None
        environment_value = environment.get("risk_index") if environment else None
        completeness_inputs = (
            bool(severities),
            vaccination is not None,
            environment is not None,
            context is not None and context.treatment is not None,
        )
        cluster_report_count = await self.session.scalar(
            select(func.count())
            .select_from(OutbreakReportMembership)
            .where(OutbreakReportMembership.disease_report_id == report.id)
        )
        veterinary_case_status = await self.session.scalar(
            select(VeterinaryCase.status)
            .where(VeterinaryCase.disease_report_id == report.id)
            .order_by(VeterinaryCase.created_at.desc())
            .limit(1)
        )
        verification_values = {
            "OPEN": Decimal("0.25"),
            "IN_REVIEW": Decimal("0.5"),
            "REFERRED": Decimal("0.75"),
            "CLOSED": Decimal("1"),
        }
        return {
            "mortality_ratio": Decimal(report.mortality_count) / Decimal(report.affected_count),
            "symptom_severity": (
                Decimal(sum(severities)) / Decimal(len(severities) * 5) if severities else None
            ),
            "vaccination_gap": (
                None if status is None else Decimal(0 if status == "CURRENT" else 1)
            ),
            "environmental_risk": (
                Decimal(str(environment_value)) if environment_value is not None else None
            ),
            "data_completeness": Decimal(sum(completeness_inputs))
            / Decimal(len(completeness_inputs)),
            "cluster_density": (
                None
                if not cluster_report_count
                else min(Decimal("1"), Decimal(cluster_report_count) / Decimal("3"))
            ),
            "verification_status": verification_values.get(veterinary_case_status),
        }

    async def triage(
        self,
        report_id: UUID,
        principal: CurrentPrincipal,
        idempotency_key: str | None = None,
    ) -> TriageResult:
        report = await self._submitted_report(report_id)
        authorize(principal, "report.read", report)
        pack = await self.session.scalar(
            select(TriageRulePack)
            .where(TriageRulePack.active.is_(True))
            .order_by(TriageRulePack.published_at.desc().nullslast())
            .limit(1)
        )
        if pack is None:
            raise DecisionConfigurationError("No active triage rule pack exists.")
        claim = None
        if idempotency_key is not None:
            claim = await claim_idempotency(
                self.session,
                principal.user_id,
                idempotency_key,
                hashlib.sha256(
                    f"triage:{report.id}:{report.snapshot_hash}:{pack.version}".encode()
                ).hexdigest(),
            )
        existing = await self.session.scalar(
            select(TriageResult).where(
                TriageResult.disease_report_id == report.id,
                TriageResult.snapshot_hash == report.snapshot_hash,
                TriageResult.rule_pack_version == pack.version,
            )
        )
        if existing is not None:
            if claim is not None and not claim.is_replay:
                await claim.store_response(200, {"result_id": str(existing.id)})
            return existing
        snapshot = await self._snapshot(report)
        rules = TriageRuleSet(
            version=pack.version,
            diseases=tuple(
                DiseaseRule(
                    disease_code=item["disease_code"],
                    positive_evidence={
                        key: float(value)
                        for key, value in item.get("positive_evidence", {}).items()
                    },
                    negative_evidence={
                        key: float(value)
                        for key, value in item.get("negative_evidence", {}).items()
                    },
                    required_fields=tuple(item.get("required_fields", [])),
                    recommended_actions=tuple(item.get("recommended_actions", [])),
                )
                for item in pack.rules
            ),
        )
        decision = RuleBasedTriageProvider().evaluate(snapshot, rules)
        result = TriageResult(
            disease_report_id=report.id,
            rule_pack_id=pack.id,
            rule_pack_version=pack.version,
            snapshot_hash=report.snapshot_hash,
            suspected_diseases=[
                {
                    "disease_code": item.disease_code,
                    "normalized_score": item.normalized_score,
                    "contributing_symptoms": list(item.contributing_symptoms),
                    "negative_evidence": list(item.negative_evidence),
                }
                for item in decision.suspected_diseases
            ],
            contributing_factors=list(decision.contributing_factors),
            missing_fields=list(decision.missing_fields),
            recommended_actions=list(decision.recommended_actions),
            data_confidence=Decimal(str(decision.data_confidence)),
            disclaimer=decision.disclaimer,
            invoked_by_id=principal.user_id,
            created_at=utc_now(),
        )
        self.session.add(result)
        await self.session.flush()
        for rule in rules.diseases:
            for code, weight in rule.positive_evidence.items():
                self.session.add(
                    TriageFinding(
                        triage_result_id=result.id,
                        disease_code=rule.disease_code,
                        evidence_code=code,
                        evidence_kind="POSITIVE",
                        matched=snapshot.signals.get(code) is True,
                        weight=Decimal(str(weight)),
                        detail={},
                    )
                )
            for code, weight in rule.negative_evidence.items():
                self.session.add(
                    TriageFinding(
                        triage_result_id=result.id,
                        disease_code=rule.disease_code,
                        evidence_code=code,
                        evidence_kind="NEGATIVE",
                        matched=snapshot.signals.get(code) is True,
                        weight=Decimal(str(weight)),
                        detail={},
                    )
                )
        await record_audit(
            self.session, principal.user_id, "report.triage", "disease_report", report.id, True
        )
        if claim is not None:
            await claim.store_response(200, {"result_id": str(result.id)})
        await self.session.flush()
        return result

    async def score_risk(
        self,
        report_id: UUID,
        principal: CurrentPrincipal,
        idempotency_key: str | None = None,
    ) -> RiskScore:
        report = await self._submitted_report(report_id)
        authorize(principal, "report.read", report)
        pack = await self.session.scalar(
            select(RiskRulePack)
            .where(RiskRulePack.active.is_(True))
            .order_by(RiskRulePack.published_at.desc().nullslast())
            .limit(1)
        )
        if pack is None:
            raise DecisionConfigurationError("No active risk rule pack exists.")
        claim = None
        if idempotency_key is not None:
            claim = await claim_idempotency(
                self.session,
                principal.user_id,
                idempotency_key,
                hashlib.sha256(
                    f"risk:{report.id}:{report.snapshot_hash}:{pack.version}".encode()
                ).hexdigest(),
            )
        existing = await self.session.scalar(
            select(RiskScore).where(
                RiskScore.disease_report_id == report.id,
                RiskScore.snapshot_hash == report.snapshot_hash,
                RiskScore.rule_pack_version == pack.version,
            )
        )
        if existing is not None:
            if claim is not None and not claim.is_replay:
                await claim.store_response(200, {"result_id": str(existing.id)})
            return existing
        factors = tuple(
            RiskFactor(name, item["source"], Decimal(str(item["weight"])))
            for name, item in sorted(pack.factors.items())
        )
        signals = await self._risk_signals(report)
        decision = RiskScorer().score(signals=signals, factors=factors, version=pack.version)
        score = RiskScore(
            disease_report_id=report.id,
            rule_pack_id=pack.id,
            rule_pack_version=pack.version,
            snapshot_hash=report.snapshot_hash,
            value=decision.value,
            category=decision.category.value,
            data_confidence=decision.data_confidence,
            missing_signals=list(decision.missing_signals),
            invoked_by_id=principal.user_id,
            created_at=utc_now(),
        )
        self.session.add(score)
        await self.session.flush()
        self.session.add_all(
            [
                RiskFactorContribution(
                    risk_score_id=score.id,
                    factor=item.factor,
                    source=item.source,
                    normalized_value=item.normalized_value,
                    weight=item.weight,
                    points=item.points,
                )
                for item in decision.contributions
            ]
        )
        if score.category in {"HIGH", "CRITICAL"}:
            responsible_vet_id = await self.session.scalar(
                select(User.id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .join(
                    StaffGeographicAssignment,
                    StaffGeographicAssignment.user_id == User.id,
                )
                .join(Location, Location.id == StaffGeographicAssignment.location_id)
                .where(
                    User.is_active.is_(True),
                    Role.code == "VETERINARIAN",
                    StaffGeographicAssignment.active.is_(True),
                    literal(report.location_path).like(Location.hierarchy_path + "%"),
                )
                .order_by(User.id)
                .limit(1)
            )
            case = await self.session.scalar(
                select(VeterinaryCase).where(
                    VeterinaryCase.disease_report_id == report.id,
                    VeterinaryCase.status != "CLOSED",
                )
            )
            if case is None:
                await self.session.execute(
                    text("SELECT set_config('app.internal_action', " "'risk.case.create', true)")
                )
                self.session.add(
                    VeterinaryCase(
                        disease_report_id=report.id,
                        assigned_veterinarian_id=responsible_vet_id,
                        status="OPEN",
                        escalation_reason=f"Automatic {score.category} risk escalation",
                    )
                )
            alert = await self.session.scalar(
                select(Alert).where(
                    Alert.disease_report_id == report.id,
                    Alert.alert_type == "RISK_ESCALATION",
                    Alert.status == "ACTIVE",
                )
            )
            if alert is None:
                self.session.add(
                    Alert(
                        disease_report_id=report.id,
                        risk_score_id=score.id,
                        recipient_id=responsible_vet_id,
                        alert_type="RISK_ESCALATION",
                        severity=score.category,
                        status="ACTIVE",
                        message=f"{score.category} livestock-health report requires review.",
                    )
                )
            await enqueue_event(
                self.session,
                "outbreak.analysis.requested",
                report.id,
                {"report_id": str(report.id), "risk_score_id": str(score.id)},
            )
            await enqueue_event(
                self.session,
                (
                    "veterinarian.notification.requested"
                    if responsible_vet_id
                    else "veterinarian.assignment.required"
                ),
                report.id,
                {
                    "report_id": str(report.id),
                    "risk_score_id": str(score.id),
                    "veterinarian_id": str(responsible_vet_id) if responsible_vet_id else None,
                },
            )
        await record_audit(
            self.session, principal.user_id, "report.risk_score", "disease_report", report.id, True
        )
        if claim is not None:
            await claim.store_response(200, {"result_id": str(score.id)})
        await self.session.flush()
        return score
