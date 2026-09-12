import hashlib
import statistics
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.base import utc_now
from app.models.geography import Location
from app.models.reports import DiseaseReport
from app.models.surveillance import (
    Outbreak,
    OutbreakReportMembership,
    OutbreakTransition,
)
from app.repositories.surveillance import (
    latest_triage_disease,
    latest_triage_diseases,
    nearby_submitted_reports,
)
from app.risk.outbreaks import (
    CandidateReport,
    OutbreakAnalyzer,
    OutbreakConfig,
    distance_km,
)
from app.services.auth import CurrentPrincipal
from app.services.authorization import ForbiddenError, authorize
from app.services.trust import claim_idempotency, enqueue_event, record_audit


class OutbreakNotFoundError(Exception):
    pass


class OutbreakConflictError(Exception):
    pass


def authorize_outbreak_transition(principal: CurrentPrincipal, location_path: str) -> None:
    if "DISTRICT_OFFICER" not in principal.roles:
        raise ForbiddenError("Only a district officer may declare or dismiss an outbreak.")
    if not principal.location_path or not location_path.startswith(principal.location_path):
        raise ForbiddenError("The outbreak is outside the officer's assigned jurisdiction.")


async def analyze_seed_report(
    session: AsyncSession,
    *,
    seed_report_id: UUID,
    principal: CurrentPrincipal,
    idempotency_key: str,
    settings: Settings,
) -> Outbreak | None:
    seed = await session.scalar(
        select(DiseaseReport).where(DiseaseReport.id == seed_report_id).with_for_update()
    )
    if seed is None or seed.status != "SUBMITTED":
        raise OutbreakNotFoundError("A submitted seed report is required.")
    authorize(principal, "report.read_identifiable", seed)
    disease_code = await latest_triage_disease(session, seed.id)
    if disease_code is None:
        raise OutbreakConflictError("The seed report requires triage before outbreak analysis.")
    request_hash = hashlib.sha256(
        f"analyze:{seed.id}:{settings.outbreak_config_version}".encode()
    ).hexdigest()
    claim = await claim_idempotency(session, principal.user_id, idempotency_key, request_hash)
    if claim.is_replay:
        outbreak_id = (claim.response_body or {}).get("outbreak_id")
        return await session.get(Outbreak, UUID(str(outbreak_id))) if outbreak_id else None

    config = OutbreakConfig(
        version=settings.outbreak_config_version,
        radius_km=Decimal(settings.outbreak_radius_km),
        window_days=settings.outbreak_window_days,
        minimum_similar_reports=settings.outbreak_minimum_reports,
        mortality_zscore_threshold=Decimal(str(settings.outbreak_mortality_zscore)),
        frequency_ratio_threshold=Decimal(str(settings.outbreak_frequency_ratio)),
    )
    nearby = await nearby_submitted_reports(
        session,
        seed,
        radius_meters=settings.outbreak_radius_km * 1000,
        earliest_onset=seed.onset_date - timedelta(days=settings.outbreak_window_days),
    )
    triage_diseases = await latest_triage_diseases(
        session,
        [report.id for report, _, _ in nearby],
    )
    trusted_rows = [
        (report, latitude, longitude)
        for report, latitude, longitude in nearby
        if triage_diseases.get(report.id) == disease_code
    ]
    ratios = [report.mortality_count / report.affected_count for report, _, _ in trusted_rows]
    mean = statistics.fmean(ratios) if ratios else 0.0
    deviation = statistics.pstdev(ratios) if len(ratios) > 1 else 0.0
    frequency_ratio = Decimal(len(trusted_rows)) / Decimal(settings.outbreak_minimum_reports)
    candidates = tuple(
        CandidateReport(
            report_id=report.id,
            disease_code=disease_code,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            observed_at=datetime.combine(report.onset_date, datetime.min.time(), UTC),
            mortality_zscore=(
                Decimal(str(((report.mortality_count / report.affected_count) - mean) / deviation))
                if deviation
                else Decimal(0)
            ),
            baseline_frequency_ratio=frequency_ratio,
        )
        for report, latitude, longitude in trusted_rows
    )
    signal = OutbreakAnalyzer().analyze(candidates, config)
    if not signal.detected:
        await claim.store_response(200, {"detected": False, "outbreak_id": None})
        return None
    deduplication_key = f"{seed.location_id}:{disease_code}:{config.version}"
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": deduplication_key},
    )
    existing = await session.scalar(
        select(Outbreak).where(
            Outbreak.location_id == seed.location_id,
            Outbreak.disease_code == disease_code,
            Outbreak.config_version == config.version,
            Outbreak.state == "POTENTIAL",
        )
    )
    if existing is not None:
        await claim.store_response(200, {"detected": True, "outbreak_id": str(existing.id)})
        return existing
    points = ", ".join(f"({item.longitude} {item.latitude})" for item in candidates)
    outbreak = Outbreak(
        location_id=seed.location_id,
        disease_code=disease_code,
        state="POTENTIAL",
        config_version=signal.config_version,
        score=signal.score,
        factors=[
            {
                "name": item.name,
                "value": str(item.value),
                "threshold": str(item.threshold),
                "matched": item.matched,
            }
            for item in signal.factors
        ],
        cluster_geometry=WKTElement(f"MULTIPOINT({points})", srid=4326),
    )
    session.add(outbreak)
    await session.flush()
    session.add_all(
        [
            OutbreakReportMembership(
                outbreak_id=outbreak.id,
                disease_report_id=item.report_id,
                distance_km=distance_km(candidates[0], item),
                included_at=utc_now(),
            )
            for item in candidates
        ]
    )
    await record_audit(
        session,
        principal.user_id,
        "outbreak.analyze",
        "outbreak",
        outbreak.id,
        True,
    )
    await enqueue_event(
        session, "outbreak.potential.created", outbreak.id, {"id": str(outbreak.id)}
    )
    await claim.store_response(200, {"detected": True, "outbreak_id": str(outbreak.id)})
    await session.flush()
    return outbreak


async def transition_outbreak(
    session: AsyncSession,
    *,
    outbreak_id: UUID,
    target_state: str,
    reason: str,
    principal: CurrentPrincipal,
    idempotency_key: str,
) -> Outbreak:
    if target_state not in {"DECLARED", "DISMISSED"}:
        raise ValueError("Unsupported outbreak transition.")
    if not reason.strip():
        raise ValueError("A decision reason is required.")
    outbreak = await session.scalar(
        select(Outbreak).where(Outbreak.id == outbreak_id).with_for_update()
    )
    if outbreak is None:
        raise OutbreakNotFoundError("Outbreak not found.")
    location_path = await session.scalar(
        select(Location.hierarchy_path).where(Location.id == outbreak.location_id)
    )
    authorize_outbreak_transition(principal, location_path or "")
    request_hash = hashlib.sha256(
        f"outbreak:{outbreak.id}:{target_state}:{reason.strip()}".encode()
    ).hexdigest()
    claim = await claim_idempotency(session, principal.user_id, idempotency_key, request_hash)
    if claim.is_replay:
        return outbreak
    if outbreak.state != "POTENTIAL":
        raise OutbreakConflictError("Only a potential outbreak may be declared or dismissed.")
    previous_state = outbreak.state
    outbreak.state = target_state
    outbreak.declared_by_id = principal.user_id
    outbreak.declared_at = utc_now()
    outbreak.decision_reason = reason.strip()
    session.add(
        OutbreakTransition(
            outbreak_id=outbreak.id,
            actor_id=principal.user_id,
            from_state=previous_state,
            to_state=target_state,
            reason=reason.strip(),
            occurred_at=utc_now(),
        )
    )
    await record_audit(
        session,
        principal.user_id,
        f"outbreak.{target_state.casefold()}",
        "outbreak",
        outbreak.id,
        True,
    )
    await enqueue_event(
        session,
        f"outbreak.{target_state.casefold()}",
        outbreak.id,
        {"id": str(outbreak.id), "reason": reason.strip()},
    )
    await claim.store_response(200, {"id": str(outbreak.id), "state": target_state})
    await session.flush()
    return outbreak
