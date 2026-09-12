from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geography import Location
from app.models.reports import Animal, Farm


async def get_farm(session: AsyncSession, farm_id: UUID) -> Farm | None:
    return await session.get(Farm, farm_id)


async def get_animal(session: AsyncSession, animal_id: UUID) -> Animal | None:
    animal = await session.get(Animal, animal_id)
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
