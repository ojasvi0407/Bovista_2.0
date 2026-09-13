from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geography import Location
from app.models.reports import Animal, Farm
from app.repositories.operations import farm_scope


async def animal_page(session, principal, *, limit, cursor=None):
    statement = (
        select(Animal)
        .join(Farm)
        .join(Location, Farm.location_id == Location.id)
        .where(Animal.deleted_at.is_(None), Farm.deleted_at.is_(None), farm_scope(principal))
    )
    if cursor:
        statement = statement.where(Animal.id < cursor)
    return list(
        (await session.scalars(statement.order_by(Animal.id.desc()).limit(limit + 1))).all()
    )


async def get_farm(session: AsyncSession, farm_id: UUID, *, lock: bool = False) -> Farm | None:
    statement = select(Farm).where(Farm.id == farm_id)
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_animal(
    session: AsyncSession, animal_id: UUID, *, lock: bool = False
) -> Animal | None:
    statement = select(Animal).where(Animal.id == animal_id)
    if lock:
        statement = statement.with_for_update()
    animal = await session.scalar(statement)
    return animal if animal is not None and animal.deleted_at is None else None


async def list_owned_animals(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[Animal]:
    statement = (
        select(Animal)
        .join(Farm, Animal.farm_id == Farm.id)
        .where(
            Farm.owner_id == owner_id,
            Farm.deleted_at.is_(None),
            Animal.deleted_at.is_(None),
        )
        .order_by(Animal.created_at, Animal.id)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


async def list_all_animals(session: AsyncSession, *, limit: int) -> list[Animal]:
    statement = (
        select(Animal)
        .where(Animal.deleted_at.is_(None))
        .order_by(Animal.created_at, Animal.id)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


async def list_animals_in_location(
    session: AsyncSession, location_path: str, *, limit: int
) -> list[Animal]:
    statement = (
        select(Animal)
        .join(Farm, Animal.farm_id == Farm.id)
        .join(Location, Farm.location_id == Location.id)
        .where(
            Animal.deleted_at.is_(None),
            Farm.deleted_at.is_(None),
            Location.hierarchy_path.startswith(location_path),
        )
        .order_by(Animal.created_at, Animal.id)
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())


async def get_farm_location_path(session: AsyncSession, farm_id: UUID) -> str | None:
    return await session.scalar(
        select(Location.hierarchy_path)
        .join(Farm, Farm.location_id == Location.id)
        .where(Farm.id == farm_id, Farm.deleted_at.is_(None))
    )
