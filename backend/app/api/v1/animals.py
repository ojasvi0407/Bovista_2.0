from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response, status

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.schemas.animals import AnimalCreate, AnimalUpdate
from app.services.animals import (
    AnimalAccessError,
    AnimalNotFoundError,
    AnimalVersionConflictError,
    FarmNotFoundError,
    create_animal,
    delete_animal,
    get_animal_by_id,
    list_animals,
    update_animal,
)
from app.services.trust import IdempotencyConflictError

router = APIRouter(prefix="/animals", tags=["animals"])


def _version_from_etag(value: str) -> int:
    try:
        return int(value.strip().strip('"'))
    except ValueError as error:
        raise ApiError(
            400, "INVALID_IF_MATCH", "If-Match must contain an animal version."
        ) from error


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    payload: AnimalCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await create_animal(session, principal, payload, idempotency_key)
        await session.commit()
        return envelope(result.data, meta={"idempotent_replay": result.replay})
    except FarmNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "FARM_NOT_FOUND", str(error)) from error
    except AnimalAccessError as error:
        await session.rollback()
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except IdempotencyConflictError as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error


@router.get("")
async def list_visible(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    try:
        return envelope(
            await list_animals(session, principal, limit=limit),
            meta={"next_cursor": None},
        )
    except AnimalAccessError as error:
        raise ApiError(403, "FORBIDDEN", str(error)) from error


@router.get("/{animal_id}")
async def get_one(
    animal_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
) -> dict[str, Any]:
    try:
        return envelope(await get_animal_by_id(session, principal, animal_id))
    except AnimalNotFoundError as error:
        raise ApiError(404, "ANIMAL_NOT_FOUND", str(error)) from error
    except AnimalAccessError as error:
        raise ApiError(403, "FORBIDDEN", str(error)) from error


@router.put("/{animal_id}")
async def update(
    animal_id: UUID,
    payload: AnimalUpdate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    if_match: Annotated[str, Header(alias="If-Match")],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await update_animal(
            session, principal, animal_id, payload, _version_from_etag(if_match), idempotency_key
        )
        await session.commit()
        return envelope(result.data, meta={"idempotent_replay": result.replay})
    except AnimalNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "ANIMAL_NOT_FOUND", str(error)) from error
    except AnimalAccessError as error:
        await session.rollback()
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except (AnimalVersionConflictError, IdempotencyConflictError) as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    animal_id: UUID,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    if_match: Annotated[str, Header(alias="If-Match")],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> Response:
    try:
        await delete_animal(
            session, principal, animal_id, _version_from_etag(if_match), idempotency_key
        )
        await session.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    except AnimalNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "ANIMAL_NOT_FOUND", str(error)) from error
    except AnimalAccessError as error:
        await session.rollback()
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except (AnimalVersionConflictError, IdempotencyConflictError) as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error
