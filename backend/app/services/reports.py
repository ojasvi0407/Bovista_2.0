import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.geography import Location
from app.models.reports import (
    Animal,
    DiseaseReport,
    DiseaseReportSymptom,
    Herd,
    ReportContextSnapshot,
    Symptom,
)
from app.repositories.reports import get_farm, get_report
from app.schemas.reports import DiseaseReportCreate, DiseaseReportView
from app.services.auth import CurrentPrincipal
from app.services.authorization import ForbiddenError
from app.services.trust import claim_idempotency, enqueue_event, record_audit


class ReportNotFoundError(Exception):
    pass


class VersionConflictError(Exception):
    pass


class InvalidReportError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MutationResult:
    data: dict[str, object]
    replay: bool = False


def _authorize_report_mutation(
    principal: CurrentPrincipal, reporter_id: UUID, location_path: str
) -> None:
    roles = set(principal.roles)
    if "ADMIN" in roles:
        return
    if "FARMER" in roles and reporter_id == principal.user_id:
        return
    if roles.intersection({"VETERINARIAN", "PARAVET"}) and principal.location_path:
        if location_path.startswith(principal.location_path):
            return
    raise ForbiddenError("Report mutation is outside the caller's role or jurisdiction.")


def _view(report: DiseaseReport) -> dict[str, object]:
    return DiseaseReportView(
        id=report.id,
        status=report.status,
        version=report.version,
        farm_id=report.farm_id,
        species=report.species,
        affected_count=report.affected_count,
        mortality_count=report.mortality_count,
        onset_date=report.onset_date,
        submitted_at=report.submitted_at,
    ).model_dump(mode="json")


def _request_hash(payload: DiseaseReportCreate) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def create_report(
    session: AsyncSession,
    principal: CurrentPrincipal,
    payload: DiseaseReportCreate,
    idempotency_key: str,
) -> MutationResult:
    claim = await claim_idempotency(
        session, principal.user_id, idempotency_key, _request_hash(payload)
    )
    if claim.is_replay:
        if claim.response_body is None:
            raise VersionConflictError("The original request is still being processed.")
        return MutationResult(claim.response_body, replay=True)

    farm = await get_farm(session, payload.farm_id)
    if farm is None:
        raise ReportNotFoundError("Farm not found.")
    location = await session.get(Location, farm.location_id)
    if location is None:
        raise InvalidReportError("The farm has no valid location.")
    _authorize_report_mutation(principal, farm.owner_id, location.hierarchy_path)
    if payload.animal_id is not None:
        animal = await session.get(Animal, payload.animal_id)
        if (
            animal is None
            or animal.deleted_at is not None
            or animal.farm_id != farm.id
            or animal.species != payload.species
        ):
            raise InvalidReportError("The animal does not belong to this farm and species.")
    if payload.herd_id is not None:
        herd = await session.get(Herd, payload.herd_id)
        if (
            herd is None
            or herd.deleted_at is not None
            or herd.farm_id != farm.id
            or herd.species != payload.species
        ):
            raise InvalidReportError("The herd does not belong to this farm and species.")
    symptom_codes = {item.code for item in payload.symptoms}
    symptoms = {
        symptom.code: symptom
        for symptom in (
            await session.scalars(
                select(Symptom).where(Symptom.code.in_(symptom_codes), Symptom.active.is_(True))
            )
        ).all()
    }
    missing = symptom_codes - symptoms.keys()
    if missing:
        raise InvalidReportError(f"Unknown symptom codes: {', '.join(sorted(missing))}")

    report = DiseaseReport(
        reporter_id=principal.user_id,
        client_generated_id=payload.client_generated_id,
        farm_id=farm.id,
        animal_id=payload.animal_id,
        herd_id=payload.herd_id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        status="DRAFT",
        species=payload.species,
        affected_count=payload.affected_count,
        mortality_count=payload.mortality_count,
        onset_date=payload.onset_date,
        report_geometry=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
        notes=payload.notes,
    )
    session.add(report)
    await session.flush()
    session.add_all(
        [
            DiseaseReportSymptom(
                disease_report_id=report.id,
                symptom_id=symptoms[item.code].id,
                symptom_code_snapshot=item.code,
                severity_snapshot=symptoms[item.code].severity,
                observed_at=item.observed_at,
            )
            for item in payload.symptoms
        ]
    )
    session.add(
        ReportContextSnapshot(
            disease_report_id=report.id,
            vaccination=payload.vaccination,
            treatment=payload.treatment,
            environment=payload.environment,
        )
    )
    data = _view(report)
    await record_audit(
        session, principal.user_id, "report.create", "disease_report", report.id, True
    )
    await enqueue_event(session, "disease_report.created", report.id, {"id": str(report.id)})
    await claim.store_response(201, data)
    await session.flush()
    return MutationResult(data)


async def submit_report(
    session: AsyncSession,
    principal: CurrentPrincipal,
    report_id: UUID,
    expected_version: int,
    idempotency_key: str,
) -> MutationResult:
    request_hash = hashlib.sha256(f"submit:{report_id}:{expected_version}".encode()).hexdigest()
    claim = await claim_idempotency(session, principal.user_id, idempotency_key, request_hash)
    if claim.is_replay and claim.response_body is not None:
        return MutationResult(claim.response_body, replay=True)
    report = await get_report(session, report_id)
    if report is None:
        raise ReportNotFoundError("Report not found.")
    _authorize_report_mutation(principal, report.reporter_id, report.location_path)
    if report.version != expected_version:
        raise VersionConflictError("The report version has changed.")
    if report.status != "DRAFT":
        raise VersionConflictError("Only a draft report can be submitted.")
    symptoms = (
        await session.scalars(
            select(DiseaseReportSymptom)
            .where(DiseaseReportSymptom.disease_report_id == report.id)
            .order_by(
                DiseaseReportSymptom.symptom_code_snapshot,
                DiseaseReportSymptom.id,
            )
        )
    ).all()
    context = await session.scalar(
        select(ReportContextSnapshot).where(ReportContextSnapshot.disease_report_id == report.id)
    )
    geometry = await session.scalar(
        select(func.ST_AsEWKT(DiseaseReport.report_geometry)).where(DiseaseReport.id == report.id)
    )
    submitted_version = report.version + 1
    snapshot = {
        "id": str(report.id),
        "farm_id": str(report.farm_id),
        "animal_id": str(report.animal_id) if report.animal_id else None,
        "herd_id": str(report.herd_id) if report.herd_id else None,
        "location_id": str(report.location_id),
        "location_path": report.location_path,
        "species": report.species,
        "affected_count": report.affected_count,
        "mortality_count": report.mortality_count,
        "onset_date": report.onset_date.isoformat(),
        "geometry": geometry,
        "notes": report.notes,
        "symptoms": [
            {
                "code": item.symptom_code_snapshot,
                "severity": item.severity_snapshot,
                "observed_at": item.observed_at.isoformat() if item.observed_at else None,
            }
            for item in symptoms
        ],
        "context": {
            "vaccination": context.vaccination if context else None,
            "treatment": context.treatment if context else None,
            "environment": context.environment if context else None,
        },
        "version": submitted_version,
    }
    report.snapshot_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report.status = "SUBMITTED"
    report.submitted_at = utc_now()
    report.version = submitted_version
    data = _view(report)
    await record_audit(
        session, principal.user_id, "report.submit", "disease_report", report.id, True
    )
    await enqueue_event(session, "disease_report.submitted", report.id, {"id": str(report.id)})
    await claim.store_response(200, data)
    await session.flush()
    return MutationResult(data)
