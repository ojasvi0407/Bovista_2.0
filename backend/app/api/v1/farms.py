from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Response

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.api.v1.clinical import Key, Limit
from app.models.reports import Farm, Herd
from app.schemas.operations import FarmCreate, FarmUpdate, HerdCreate, HerdUpdate
from app.services.farms import create_record, farm_view, list_records, mutate_record, scoped_record
from app.services.operation_commands import command, require_role

router = APIRouter(tags=["farms and herds"])
Version = Annotated[str, Header(alias="If-Match")]


def version_number(value):
    try:
        result = int(value.strip('"'))
        if result < 1:
            raise ValueError
        return result
    except ValueError as error:
        raise ApiError(
            400, "INVALID_IF_MATCH", "If-Match must contain a positive version."
        ) from error


@router.post("/farms", status_code=201)
async def create_farms(
    payload: FarmCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "FARMER")
    return await command(
        session,
        principal,
        idempotency_key,
        "farms.create",
        payload.model_dump(mode="json"),
        lambda: create_record(session, principal, Farm, payload),
        201,
    )


@router.get("/farms")
async def list_farms(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    return await list_records(session, principal, Farm, limit=limit, cursor=cursor)


@router.get("/farms/{record_id}")
async def get_farms(
    record_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    response: Response,
):
    record = await scoped_record(session, principal, Farm, record_id)
    response.headers["ETag"] = f'"{record.version}"'
    return envelope(farm_view(record))


@router.put("/farms/{record_id}")
async def update_farms(
    record_id: UUID,
    payload: FarmUpdate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Version,
):
    require_role(principal, "FARMER", "ADMIN")
    version = version_number(if_match)
    return await command(
        session,
        principal,
        idempotency_key,
        "farms.update",
        {
            "id": str(record_id),
            "version": version,
            **payload.model_dump(mode="json", exclude_unset=True),
        },
        lambda: mutate_record(session, principal, Farm, record_id, payload, version),
    )


@router.delete("/farms/{record_id}", status_code=204)
async def delete_farms(
    record_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Version,
):
    require_role(principal, "FARMER", "ADMIN")
    version = version_number(if_match)
    await command(
        session,
        principal,
        idempotency_key,
        "farms.delete",
        {"id": str(record_id), "version": version},
        lambda: mutate_record(session, principal, Farm, record_id, None, version, delete=True),
    )
    return Response(status_code=204)


@router.post("/herds", status_code=201)
async def create_herds(
    payload: HerdCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "FARMER", "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "herds.create",
        payload.model_dump(mode="json"),
        lambda: create_record(session, principal, Herd, payload),
        201,
    )


@router.get("/herds")
async def list_herds(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    return await list_records(session, principal, Herd, limit=limit, cursor=cursor)


@router.get("/herds/{record_id}")
async def get_herds(
    record_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    response: Response,
):
    record = await scoped_record(session, principal, Herd, record_id)
    response.headers["ETag"] = f'"{record.version}"'
    return envelope(farm_view(record))


@router.put("/herds/{record_id}")
async def update_herds(
    record_id: UUID,
    payload: HerdUpdate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Version,
):
    require_role(principal, "FARMER", "ADMIN")
    version = version_number(if_match)
    return await command(
        session,
        principal,
        idempotency_key,
        "herds.update",
        {
            "id": str(record_id),
            "version": version,
            **payload.model_dump(mode="json", exclude_unset=True),
        },
        lambda: mutate_record(session, principal, Herd, record_id, payload, version),
    )


@router.delete("/herds/{record_id}", status_code=204)
async def delete_herds(
    record_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Version,
):
    require_role(principal, "FARMER", "ADMIN")
    version = version_number(if_match)
    await command(
        session,
        principal,
        idempotency_key,
        "herds.delete",
        {"id": str(record_id), "version": version},
        lambda: mutate_record(session, principal, Herd, record_id, None, version, delete=True),
    )
    return Response(status_code=204)
