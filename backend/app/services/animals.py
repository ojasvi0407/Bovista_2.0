import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.reports import Animal
from app.repositories.animals import (
    get_animal,
    get_farm,
    get_farm_location_path,
    list_all_animals,
    list_animals_in_location,
    list_owned_animals,
)
from app.schemas.animals import AnimalCreate, AnimalUpdate, AnimalView
from app.services.auth import CurrentPrincipal
from app.services.trust import claim_idempotency, enqueue_event, record_audit


class AnimalAccessError(Exception):
    pass


class FarmNotFoundError(Exception):
    pass


class AnimalNotFoundError(Exception):
    pass


class AnimalVersionConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AnimalMutationResult:
    data: dict[str, object]
    replay: bool = False


def _view(animal: Animal) -> dict[str, object]:
    return AnimalView(
        id=animal.id,
        farm_id=animal.farm_id,
        herd_id=animal.herd_id,
        species=animal.species,
        tag_number=animal.tag_number,
        sex=animal.sex,
        birth_date=animal.birth_date,
        version=animal.version,
    ).model_dump(mode="json")


def _request_hash(payload: AnimalCreate) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _can_manage_farm(principal: CurrentPrincipal, owner_id: UUID) -> bool:
    return "ADMIN" in principal.roles or (
        "FARMER" in principal.roles and principal.user_id == owner_id
    )


def _can_read_farm(
    principal: CurrentPrincipal,
    owner_id: UUID,
    location_path: str | None,
) -> bool:
    if _can_manage_farm(principal, owner_id):
        return True
    return bool(
        set(principal.roles).intersection({"VETERINARIAN", "PARAVET"})
        and principal.location_path
        and location_path
        and location_path.startswith(principal.location_path)
    )


async def create_animal(
    session: AsyncSession,
    principal: CurrentPrincipal,
    payload: AnimalCreate,
    idempotency_key: str,
) -> AnimalMutationResult:
    claim = await claim_idempotency(
        session, principal.user_id, idempotency_key, _request_hash(payload)
    )
    if claim.is_replay:
        if claim.response_body is None:
            raise AnimalAccessError("The original request is still being processed.")
        return AnimalMutationResult(claim.response_body, replay=True)

    farm = await get_farm(session, payload.farm_id)
    if farm is None or farm.deleted_at is not None:
        raise FarmNotFoundError("Farm not found.")
    if not _can_manage_farm(principal, farm.owner_id):
        raise AnimalAccessError("You cannot create animals for this farm.")

    animal = Animal(
        farm_id=farm.id,
        species=payload.species,
        tag_number=payload.tag_number,
        sex=payload.sex,
        birth_date=payload.birth_date,
    )
    session.add(animal)
    await session.flush()
    data = _view(animal)
    await record_audit(session, principal.user_id, "animal.create", "animal", animal.id, True)
    await enqueue_event(session, "animal.created", animal.id, {"id": str(animal.id)})
    await claim.store_response(201, data)
    return AnimalMutationResult(data)


async def list_animals(
    session: AsyncSession, principal: CurrentPrincipal, *, limit: int = 50
) -> list[dict[str, object]]:
    if "FARMER" in principal.roles:
        animals = await list_owned_animals(session, principal.user_id, limit=limit)
        return [_view(animal) for animal in animals]
    if "ADMIN" in principal.roles:
        return [_view(animal) for animal in await list_all_animals(session, limit=limit)]
    if set(principal.roles).intersection({"VETERINARIAN", "PARAVET"}):
        if not principal.location_path:
            raise AnimalAccessError("A geographic assignment is required to list animals.")
        animals = await list_animals_in_location(
            session,
            principal.location_path,
            limit=limit,
        )
        return [_view(animal) for animal in animals]
    raise AnimalAccessError("You cannot list animals.")


async def get_animal_by_id(
    session: AsyncSession, principal: CurrentPrincipal, animal_id: UUID
) -> dict[str, object]:
    animal = await get_animal(session, animal_id)
    if animal is None:
        raise AnimalNotFoundError("Animal not found.")
    farm = await get_farm(session, animal.farm_id)
    location_path = await get_farm_location_path(session, animal.farm_id)
    if farm is None or not _can_read_farm(principal, farm.owner_id, location_path):
        raise AnimalAccessError("You cannot access this animal.")
    return _view(animal)


async def update_animal(
    session: AsyncSession,
    principal: CurrentPrincipal,
    animal_id: UUID,
    payload: AnimalUpdate,
    expected_version: int,
    idempotency_key: str,
) -> AnimalMutationResult:
    request_hash = hashlib.sha256(
        json.dumps(
            {
                "animal_id": str(animal_id),
                "version": expected_version,
                **payload.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    claim = await claim_idempotency(session, principal.user_id, idempotency_key, request_hash)
    if claim.is_replay:
        if claim.response_body is None:
            raise AnimalVersionConflictError("The original request is still being processed.")
        return AnimalMutationResult(claim.response_body, replay=True)
    animal = await get_animal(session, animal_id)
    if animal is None:
        raise AnimalNotFoundError("Animal not found.")
    farm = await get_farm(session, animal.farm_id)
    if farm is None or not _can_manage_farm(principal, farm.owner_id):
        raise AnimalAccessError("You cannot update this animal.")
    if animal.version != expected_version:
        raise AnimalVersionConflictError("The animal version has changed.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(animal, field, value)
    animal.version += 1
    await session.flush()
    data = _view(animal)
    await record_audit(session, principal.user_id, "animal.update", "animal", animal.id, True)
    await enqueue_event(session, "animal.updated", animal.id, {"id": str(animal.id)})
    await claim.store_response(200, data)
    return AnimalMutationResult(data)


async def delete_animal(
    session: AsyncSession,
    principal: CurrentPrincipal,
    animal_id: UUID,
    expected_version: int,
    idempotency_key: str,
) -> bool:
    request_hash = hashlib.sha256(f"delete:{animal_id}:{expected_version}".encode()).hexdigest()
    claim = await claim_idempotency(session, principal.user_id, idempotency_key, request_hash)
    if claim.is_replay:
        return True
    animal = await get_animal(session, animal_id)
    if animal is None:
        raise AnimalNotFoundError("Animal not found.")
    farm = await get_farm(session, animal.farm_id)
    if farm is None or not _can_manage_farm(principal, farm.owner_id):
        raise AnimalAccessError("You cannot delete this animal.")
    if animal.version != expected_version:
        raise AnimalVersionConflictError("The animal version has changed.")
    animal.deleted_at = utc_now()
    animal.version += 1
    await record_audit(session, principal.user_id, "animal.delete", "animal", animal.id, True)
    await enqueue_event(session, "animal.deleted", animal.id, {"id": str(animal.id)})
    await claim.store_response(204, {})
    return True
