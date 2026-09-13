from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.responses import envelope
from app.models.clinical import Vaccination
from app.models.operations import Treatment
from app.schemas.operations import ReasonCommand, TreatmentCreate, VaccinationCreate
from app.services.clinical import clinical_detail, list_clinical, record_clinical, reverse_clinical
from app.services.operation_commands import command, require_role

router = APIRouter(tags=["clinical"])
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post("/vaccinations", status_code=201)
async def vaccination_create(
    payload: VaccinationCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "PARAVET", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "vaccination.create",
        payload.model_dump(mode="json"),
        lambda: record_clinical(session, principal, payload, vaccination=True),
        201,
    )


@router.post("/treatments", status_code=201)
async def treatment_create(
    payload: TreatmentCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "treatment.create",
        payload.model_dump(mode="json"),
        lambda: record_clinical(session, principal, payload, vaccination=False),
        201,
    )


@router.get("/vaccinations/due")
async def vaccinations_due(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    return await list_clinical(
        session, principal, Vaccination, limit=limit, cursor=cursor, due=True
    )


@router.get("/vaccinations")
async def vaccinations_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
    animal_id: UUID | None = None,
):
    return await list_clinical(
        session, principal, Vaccination, limit=limit, cursor=cursor, animal_id=animal_id
    )


@router.get("/treatments")
async def treatments_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
    animal_id: UUID | None = None,
):
    return await list_clinical(
        session, principal, Treatment, limit=limit, cursor=cursor, animal_id=animal_id
    )


@router.get("/vaccinations/{record_id}")
async def vaccination_get(
    record_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    return envelope(await clinical_detail(session, principal, Vaccination, record_id))


@router.get("/treatments/{record_id}")
async def treatment_get(
    record_id: UUID, principal: CurrentPrincipalDependency, session: PrincipalSessionDependency
):
    return envelope(await clinical_detail(session, principal, Treatment, record_id))


@router.post("/vaccinations/{record_id}/reverse")
async def vaccination_reverse(
    record_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "vaccination.reverse",
        {"id": str(record_id), **payload.model_dump()},
        lambda: reverse_clinical(session, principal, Vaccination, record_id, payload.reason),
    )


@router.post("/treatments/{record_id}/reverse")
async def treatment_reverse(
    record_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "VETERINARIAN", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "treatment.reverse",
        {"id": str(record_id), **payload.model_dump()},
        lambda: reverse_clinical(session, principal, Treatment, record_id, payload.reason),
    )
