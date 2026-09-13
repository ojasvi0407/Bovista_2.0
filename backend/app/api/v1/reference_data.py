from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import Field
from sqlalchemy import func, select

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.api.v1.clinical import Key, Limit
from app.db.base import utc_now
from app.models.geography import Location
from app.models.reports import Disease, Symptom
from app.schemas.operations import Name, ReasonCommand, StrictInput
from app.services.operation_commands import changed, command, require_role

router = APIRouter(tags=["reference data"])
LEVELS = ("COUNTRY", "STATE", "DISTRICT", "BLOCK", "VILLAGE")


class LocationCreate(StrictInput):
    parent_id: UUID | None = None
    level: Literal["COUNTRY", "STATE", "DISTRICT", "BLOCK", "VILLAGE"]
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: Name


class DiseaseCreate(StrictInput):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: Name


class SymptomCreate(StrictInput):
    code: str = Field(min_length=1, max_length=60, pattern=r"^[A-Z0-9_-]+$")
    name: Name
    severity: int = Field(ge=1, le=5)


@router.get("/locations")
async def location_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
    parent_id: UUID | None = None,
):
    statement = select(Location)
    if parent_id:
        statement = statement.where(Location.parent_id == parent_id)
    if cursor:
        statement = statement.where(Location.id < cursor)
    rows = list(
        (await session.scalars(statement.order_by(Location.id.desc()).limit(limit + 1))).all()
    )
    return envelope(
        [
            {
                "id": str(r.id),
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "code": r.code,
                "name": r.name,
                "level": r.level,
            }
            for r in rows[:limit]
        ],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )


@router.post("/locations", status_code=201)
async def location_create(
    payload: LocationCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")

    async def work():
        parent = await session.get(Location, payload.parent_id) if payload.parent_id else None
        index = LEVELS.index(payload.level)
        if (index == 0 and payload.parent_id is not None) or (
            index > 0 and (parent is None or parent.level != LEVELS[index - 1])
        ):
            raise ApiError(422, "INVALID_HIERARCHY", "Location parent must be the preceding level.")
        path = (parent.hierarchy_path if parent else "/") + payload.code + "/"
        if len(path) > 500:
            raise ApiError(422, "INVALID_HIERARCHY", "Location hierarchy is too long.")
        record = Location(**payload.model_dump(), hierarchy_path=path)
        session.add(record)
        return await changed(session, principal, "location.create", record)

    return await command(
        session,
        principal,
        idempotency_key,
        "location.create",
        payload.model_dump(mode="json"),
        work,
        201,
    )


@router.get("/diseases")
async def disease_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    statement = select(Disease).where(Disease.active.is_(True))
    if cursor:
        statement = statement.where(Disease.id < cursor)
    rows = list(
        (await session.scalars(statement.order_by(Disease.id.desc()).limit(limit + 1))).all()
    )
    return envelope(
        [
            {"id": str(r.id), "code": r.code, "name": r.name, "revision": r.revision}
            for r in rows[:limit]
        ],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )


@router.get("/symptoms")
async def symptom_list(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    statement = select(Symptom).where(Symptom.active.is_(True))
    if cursor:
        statement = statement.where(Symptom.id < cursor)
    rows = list(
        (await session.scalars(statement.order_by(Symptom.id.desc()).limit(limit + 1))).all()
    )
    return envelope(
        [
            {
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "severity": r.severity,
                "revision": r.revision,
            }
            for r in rows[:limit]
        ],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )


@router.post("/diseases", status_code=201)
async def disease_create(
    payload: DiseaseCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")

    async def work():
        record = Disease(**payload.model_dump())
        session.add(record)
        return await changed(session, principal, "disease.create", record)

    return await command(
        session, principal, idempotency_key, "disease.create", payload.model_dump(), work, 201
    )


@router.post("/symptoms", status_code=201)
async def symptom_create(
    payload: SymptomCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")

    async def work():
        record = Symptom(**payload.model_dump())
        session.add(record)
        return await changed(session, principal, "symptom.create", record)

    return await command(
        session, principal, idempotency_key, "symptom.create", payload.model_dump(), work, 201
    )


async def publish_reference_version(session, principal, model, code, payload):
    current = await session.scalar(
        select(model).where(model.code == code, model.active.is_(True)).with_for_update()
    )
    latest_revision = await session.scalar(
        select(func.max(model.revision)).where(model.code == code)
    )
    if latest_revision is None:
        raise ApiError(404, "NOT_FOUND", "Reference code not found.")
    if current is not None:
        current.active = False
        current.retired_at = utc_now()
    values = payload.model_dump(exclude={"code"})
    record = model(code=code, revision=latest_revision + 1, **values)
    session.add(record)
    return await changed(session, principal, f"{model.__tablename__}.publish", record)


@router.post("/diseases/{code}/versions", status_code=201)
async def disease_publish(
    code: str,
    payload: DiseaseCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")
    if payload.code != code:
        raise ApiError(422, "CODE_MISMATCH", "Path and payload codes must match.")
    return await command(
        session,
        principal,
        idempotency_key,
        "disease.publish",
        payload.model_dump(),
        lambda: publish_reference_version(session, principal, Disease, code, payload),
        201,
    )


@router.post("/symptoms/{code}/versions", status_code=201)
async def symptom_publish(
    code: str,
    payload: SymptomCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")
    if payload.code != code:
        raise ApiError(422, "CODE_MISMATCH", "Path and payload codes must match.")
    return await command(
        session,
        principal,
        idempotency_key,
        "symptom.publish",
        payload.model_dump(),
        lambda: publish_reference_version(session, principal, Symptom, code, payload),
        201,
    )


@router.post("/{kind}/{record_id}/retire")
async def reference_retire(
    kind: Literal["diseases", "symptoms"],
    record_id: UUID,
    payload: ReasonCommand,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")
    model = Disease if kind == "diseases" else Symptom

    async def work():
        record = await session.scalar(
            select(model).where(model.id == record_id, model.active.is_(True)).with_for_update()
        )
        if record is None:
            raise ApiError(404, "NOT_FOUND", "Active reference version not found.")
        record.active = False
        record.retired_at = utc_now()
        return await changed(session, principal, f"{kind}.retire", record)

    return await command(
        session,
        principal,
        idempotency_key,
        f"{kind}.retire",
        {"id": str(record_id), **payload.model_dump()},
        work,
    )
