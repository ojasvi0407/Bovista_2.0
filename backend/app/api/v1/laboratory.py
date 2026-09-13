from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.api.v1.clinical import Key, Limit
from app.models.operations import LaboratoryResult, LaboratoryTransition
from app.schemas.operations import ReasonCommand, ResultCreate, SampleCreate
from app.services.laboratory import TRANSITIONS, list_samples, refer, sample_in_scope, transition
from app.services.operation_commands import command, require_role, view

router = APIRouter(prefix="/lab", tags=["laboratory"])


@router.post("/samples", status_code=201)
async def sample_create(
    payload: SampleCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "PARAVET", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.refer",
        payload.model_dump(mode="json"),
        lambda: refer(session, principal, payload),
        201,
    )


@router.get("/samples")
async def samples_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
    status: (
        Literal["REFERRED", "COLLECTED", "RECEIVED", "PROCESSING", "RESULTED", "REVIEWED"] | None
    ) = None,
):
    return await list_samples(session, principal, limit=limit, cursor=cursor, status=status)


@router.get("/results")
async def results_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    return await list_samples(session, principal, limit=limit, cursor=cursor, results=True)


@router.get("/results/{result_id}")
async def result_detail(
    result_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    result = await session.scalar(select(LaboratoryResult).where(LaboratoryResult.id == result_id))
    if result is None:
        raise ApiError(404, "NOT_FOUND", "Laboratory result not found.")
    await sample_in_scope(session, principal, result.sample_id)
    return envelope(view(result))


@router.get("/samples/{sample_id}")
async def sample_detail(
    sample_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    sample = await sample_in_scope(session, principal, sample_id)
    return envelope(view(sample))


@router.get("/samples/{sample_id}/history")
async def sample_history(
    sample_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    await sample_in_scope(session, principal, sample_id)
    rows = await session.scalars(
        select(LaboratoryTransition)
        .where(LaboratoryTransition.sample_id == sample_id)
        .order_by(LaboratoryTransition.occurred_at)
    )
    return envelope([view(row) for row in rows])


@router.post("/samples/{sample_id}/collect")
async def sample_collect(
    sample_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, *TRANSITIONS["collect"][2])
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.collect",
        {"id": str(sample_id), **payload.model_dump(mode="json")},
        lambda: transition(session, principal, sample_id, "collect", payload),
    )


@router.post("/samples/{sample_id}/receive")
async def sample_receive(
    sample_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, *TRANSITIONS["receive"][2])
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.receive",
        {"id": str(sample_id), **payload.model_dump(mode="json")},
        lambda: transition(session, principal, sample_id, "receive", payload),
    )


@router.post("/samples/{sample_id}/start-processing")
async def sample_start_processing(
    sample_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, *TRANSITIONS["start-processing"][2])
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.start-processing",
        {"id": str(sample_id), **payload.model_dump(mode="json")},
        lambda: transition(session, principal, sample_id, "start-processing", payload),
    )


@router.post("/samples/{sample_id}/result", status_code=201)
async def sample_result(
    sample_id: UUID,
    payload: ResultCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, *TRANSITIONS["result"][2])
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.result",
        {"id": str(sample_id), **payload.model_dump(mode="json")},
        lambda: transition(session, principal, sample_id, "result", payload),
        201,
    )


@router.post("/samples/{sample_id}/review")
async def sample_review(
    sample_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, *TRANSITIONS["review"][2])
    return await command(
        session,
        principal,
        idempotency_key,
        "laboratory.review",
        {"id": str(sample_id), **payload.model_dump(mode="json")},
        lambda: transition(session, principal, sample_id, "review", payload),
    )
