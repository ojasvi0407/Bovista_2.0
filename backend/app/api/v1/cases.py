from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import exists, select

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.api.v1.clinical import Key, Limit
from app.db.base import utc_now
from app.models.laboratory import LaboratorySample
from app.models.operations import CaseTransition
from app.models.reports import DiseaseReport
from app.models.surveillance import VeterinaryCase
from app.repositories.operations import report_scope
from app.schemas.operations import ReasonCommand
from app.services.operation_commands import changed, command, require_role, view

router = APIRouter(prefix="/cases", tags=["veterinary cases"])
STATES = {
    "review": ("OPEN", "IN_REVIEW"),
    "refer": ("IN_REVIEW", "REFERRED"),
    "resume": ("REFERRED", "IN_REVIEW"),
    "close": ("IN_REVIEW", "CLOSED"),
}


async def scoped_case(session, principal, case_id, lock=False):
    statement = (
        select(VeterinaryCase)
        .join(DiseaseReport)
        .where(
            VeterinaryCase.id == case_id,
            DiseaseReport.deleted_at.is_(None),
            report_scope(principal),
        )
    )
    if lock:
        statement = statement.with_for_update(of=VeterinaryCase)
    case = await session.scalar(statement)
    if case is None:
        raise ApiError(404, "CASE_NOT_FOUND", "Case not found.")
    return case


@router.get("")
async def case_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    statement = (
        select(VeterinaryCase)
        .join(DiseaseReport)
        .where(report_scope(principal), DiseaseReport.deleted_at.is_(None))
    )
    if cursor:
        statement = statement.where(VeterinaryCase.id < cursor)
    rows = list(
        (await session.scalars(statement.order_by(VeterinaryCase.id.desc()).limit(limit + 1))).all()
    )
    return envelope(
        [view(row) for row in rows[:limit]],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )


@router.get("/{case_id}")
async def case_detail(
    case_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    return envelope(view(await scoped_case(session, principal, case_id)))


@router.get("/{case_id}/history")
async def case_history(
    case_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    await scoped_case(session, principal, case_id)
    statement = select(CaseTransition).where(CaseTransition.case_id == case_id)
    if cursor:
        statement = statement.where(CaseTransition.id < cursor)
    rows = list(
        (await session.scalars(statement.order_by(CaseTransition.id.desc()).limit(limit + 1))).all()
    )
    return envelope(
        [view(row) for row in rows[:limit]],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )


@router.post("/{case_id}/{action}")
async def case_transition(
    case_id: UUID,
    action: str,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "ADMIN")
    if action not in STATES:
        raise ApiError(404, "NOT_FOUND", "Case action not found.")

    async def work():
        case = await scoped_case(session, principal, case_id, lock=True)
        before, after = STATES[action]
        if case.status != before:
            raise ApiError(409, "INVALID_TRANSITION", f"This action requires a {before} case.")
        if action == "close" and await session.scalar(
            select(
                exists().where(
                    LaboratorySample.disease_report_id == case.disease_report_id,
                    LaboratorySample.status != "REVIEWED",
                )
            )
        ):
            raise ApiError(409, "CONFLICT", "Review outstanding laboratory samples before closure.")
        case.status = after
        if action == "review":
            case.assigned_veterinarian_id = principal.user_id
        if action == "close":
            case.closed_at = utc_now()
        session.add(
            CaseTransition(
                case_id=case.id,
                actor_id=principal.user_id,
                from_state=before,
                to_state=after,
                reason=payload.reason,
            )
        )
        return await changed(session, principal, f"case.{action}", case)

    return await command(
        session,
        principal,
        idempotency_key,
        f"case.{action}",
        {"id": str(case_id), **payload.model_dump()},
        work,
    )
