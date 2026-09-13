from sqlalchemy import exists, select

from app.api.errors import ApiError
from app.db.base import utc_now
from app.models.geography import Location
from app.models.reports import Animal, Farm, Herd
from app.repositories.operations import farm_scope
from app.services.operation_commands import changed, require_role, view


def farm_view(record):
    if isinstance(record, Farm):
        return {key: value for key, value in view_without_geometry(record).items()}
    return view(record)


def view_without_geometry(record):
    from fastapi.encoders import jsonable_encoder

    return jsonable_encoder(
        {c.name: getattr(record, c.name) for c in record.__table__.columns if c.name != "geometry"}
    )


async def scoped_record(session, principal, model, record_id, *, write=False):
    statement = select(model)
    if model is Herd:
        statement = statement.join(Farm, Herd.farm_id == Farm.id)
    statement = statement.join(Location, Farm.location_id == Location.id).where(
        model.id == record_id,
        model.deleted_at.is_(None),
        Farm.deleted_at.is_(None),
        farm_scope(principal),
    )
    if write:
        require_role(principal, "FARMER", "ADMIN")
        statement = statement.with_for_update(of=model)
    record = await session.scalar(statement)
    if record is None:
        raise ApiError(404, "NOT_FOUND", "Record not found.")
    return record


async def create_record(session, principal, model, payload):
    require_role(principal, "FARMER", "ADMIN")
    if model is Farm:
        require_role(principal, "FARMER")
        if await session.get(Location, payload.location_id) is None:
            raise ApiError(404, "LOCATION_NOT_FOUND", "Location not found.")
        record = Farm(**payload.model_dump(), owner_id=principal.user_id)
    else:
        await scoped_record(session, principal, Farm, payload.farm_id, write=True)
        record = Herd(**payload.model_dump())
    session.add(record)
    await session.flush()
    # Farm geometry is intentionally absent from create payloads and response.
    await changed(session, principal, f"{model.__tablename__}.create", record)
    return farm_view(record)


async def mutate_record(session, principal, model, record_id, payload, version, *, delete=False):
    record = await scoped_record(session, principal, model, record_id, write=True)
    if record.version != version:
        raise ApiError(409, "CONFLICT", "The record version has changed.")
    if delete:
        if model is Farm:
            children = await session.scalar(
                select(exists().where(Animal.farm_id == record.id, Animal.deleted_at.is_(None)))
            )
            children = children or await session.scalar(
                select(exists().where(Herd.farm_id == record.id, Herd.deleted_at.is_(None)))
            )
        else:
            children = await session.scalar(
                select(exists().where(Animal.herd_id == record.id, Animal.deleted_at.is_(None)))
            )
        if children:
            raise ApiError(409, "CONFLICT", "Archive active animals and herds first.")
        record.deleted_at = utc_now()
    else:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
    record.version += 1
    await changed(
        session, principal, f"{model.__tablename__}.{'archive' if delete else 'update'}", record
    )
    return farm_view(record)


async def list_records(session, principal, model, *, limit, cursor):
    statement = select(model)
    if model is Herd:
        statement = statement.join(Farm)
    statement = statement.join(Location, Farm.location_id == Location.id).where(
        farm_scope(principal), Farm.deleted_at.is_(None), model.deleted_at.is_(None)
    )
    if cursor:
        statement = statement.where(model.id < cursor)
    rows = list((await session.scalars(statement.order_by(model.id.desc()).limit(limit + 1))).all())
    return {
        "data": [farm_view(row) for row in rows[:limit]],
        "meta": {"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
        "error": None,
    }
