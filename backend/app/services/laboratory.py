from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.api.errors import ApiError
from app.db.base import utc_now, uuid7
from app.models.laboratory import LaboratorySample
from app.models.operations import CaseTransition, LaboratoryResult, LaboratoryTransition
from app.models.reports import DiseaseReport
from app.models.surveillance import Alert, VeterinaryCase
from app.repositories.operations import report_in_scope, report_scope
from app.services.operation_commands import changed, require_role, view

TRANSITIONS = {
    "collect": ("REFERRED", "COLLECTED", ("VETERINARIAN", "PARAVET", "ADMIN"), "collected_at"),
    "receive": ("COLLECTED", "RECEIVED", ("LAB_TECHNICIAN", "ADMIN"), "received_at"),
    "start-processing": ("RECEIVED", "PROCESSING", ("LAB_TECHNICIAN", "ADMIN"), None),
    "result": ("PROCESSING", "RESULTED", ("LAB_TECHNICIAN", "ADMIN"), "resulted_at"),
    "review": ("RESULTED", "REVIEWED", ("VETERINARIAN", "ADMIN"), "reviewed_at"),
}


async def refer(session, principal, payload):
    require_role(principal, "VETERINARIAN", "PARAVET", "ADMIN")
    report = await report_in_scope(session, principal, payload.disease_report_id, write=True)
    if report.status != "SUBMITTED":
        raise ApiError(409, "CONFLICT", "Submit the report before laboratory referral.")
    case = await session.scalar(
        select(VeterinaryCase)
        .where(
            VeterinaryCase.disease_report_id == report.id,
            VeterinaryCase.status != "CLOSED",
        )
        .with_for_update()
    )
    if case is None or case.status != "IN_REVIEW":
        raise ApiError(
            409,
            "CONFLICT",
            "An in-review veterinary case is required for laboratory referral.",
        )
    case.status = "REFERRED"
    session.add(
        CaseTransition(
            case_id=case.id,
            actor_id=principal.user_id,
            from_state="IN_REVIEW",
            to_state="REFERRED",
            reason="Laboratory referral",
        )
    )
    sample = LaboratorySample(**payload.model_dump(), created_by_id=principal.user_id)
    session.add(sample)
    await session.flush()
    session.add(
        LaboratoryTransition(
            sample_id=sample.id,
            actor_id=principal.user_id,
            from_state="NONE",
            to_state="REFERRED",
            reason="Laboratory referral",
        )
    )
    return await changed(session, principal, "laboratory.referred", sample)


async def sample_in_scope(session, principal, sample_id, *, lock=False):
    statement = (
        select(LaboratorySample)
        .join(DiseaseReport)
        .where(
            LaboratorySample.id == sample_id,
            DiseaseReport.deleted_at.is_(None),
            report_scope(principal, lab=True),
        )
    )
    if lock:
        statement = statement.with_for_update(of=LaboratorySample)
    sample = await session.scalar(statement)
    if sample is None:
        raise ApiError(404, "SAMPLE_NOT_FOUND", "Laboratory sample not found.")
    return sample


async def transition(session, principal, sample_id, action, payload):
    before, after, roles, timestamp = TRANSITIONS[action]
    require_role(principal, *roles)
    sample = await sample_in_scope(session, principal, sample_id, lock=True)
    if sample.status != before:
        raise ApiError(409, "INVALID_TRANSITION", f"This action requires a {before} sample.")
    sample.status = after
    if timestamp:
        setattr(sample, timestamp, utc_now())
    session.add(
        LaboratoryTransition(
            sample_id=sample.id,
            actor_id=principal.user_id,
            from_state=before,
            to_state=after,
            reason="Laboratory result published" if action == "result" else payload.reason,
        )
    )
    result = None
    if action == "result":
        result = LaboratoryResult(
            sample_id=sample.id, published_by_id=principal.user_id, **payload.model_dump()
        )
        session.add(result)
        report = await report_in_scope(session, principal, sample.disease_report_id)
        # The partial unique index coalesces an outstanding report notification.
        await session.execute(
            insert(Alert)
            .values(
                id=uuid7(),
                disease_report_id=report.id,
                recipient_id=report.reporter_id,
                alert_type="LAB_RESULT",
                severity="MEDIUM",
                status="ACTIVE",
                message="A laboratory result is available for veterinary review.",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            .on_conflict_do_nothing()
        )
    await changed(session, principal, f"laboratory.{action}", sample)
    if result:
        return await changed(session, principal, "laboratory.result.published", result)
    return view(sample)


async def list_samples(session, principal, *, limit, cursor, status=None, results=False):
    model = LaboratoryResult if results else LaboratorySample
    statement = select(model)
    if results:
        statement = statement.join(
            LaboratorySample, LaboratoryResult.sample_id == LaboratorySample.id
        )
    statement = statement.join(
        DiseaseReport, LaboratorySample.disease_report_id == DiseaseReport.id
    ).where(DiseaseReport.deleted_at.is_(None), report_scope(principal, lab=True))
    if cursor:
        statement = statement.where(model.id < cursor)
    if status:
        statement = statement.where(LaboratorySample.status == status)
    rows = list((await session.scalars(statement.order_by(model.id.desc()).limit(limit + 1))).all())
    return {
        "data": [view(row) for row in rows[:limit]],
        "meta": {"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
        "error": None,
    }
