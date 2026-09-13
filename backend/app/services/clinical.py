from datetime import date

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import aliased

from app.api.errors import ApiError
from app.models.clinical import Vaccination
from app.models.geography import Location
from app.models.operations import ClinicalReversal, Treatment
from app.models.reports import Animal, Farm
from app.models.surveillance import VeterinaryCase
from app.repositories.operations import animal_in_scope, farm_scope, report_in_scope
from app.services.operation_commands import changed, require_role, view


async def record_clinical(session, principal, payload, *, vaccination: bool):
    require_role(
        principal,
        *(("VETERINARIAN", "PARAVET", "ADMIN") if vaccination else ("VETERINARIAN", "ADMIN")),
    )
    animal = await animal_in_scope(session, principal, payload.animal_id, lock=True)
    values = payload.model_dump()
    if vaccination:
        record = Vaccination(**values, administered_by_id=principal.user_id)
    else:
        case = await session.scalar(
            select(VeterinaryCase).where(VeterinaryCase.id == payload.case_id).with_for_update()
        )
        if case is None:
            raise ApiError(404, "CASE_NOT_FOUND", "Case not found.")
        report = await report_in_scope(session, principal, case.disease_report_id, write=True)
        if report.farm_id != animal.farm_id or (
            report.animal_id is not None and report.animal_id != animal.id
        ):
            raise ApiError(
                409, "CONFLICT", "Animal and case must concern the same farm and animal."
            )
        if case.status == "CLOSED":
            raise ApiError(409, "CONFLICT", "Closed cases cannot receive new treatment records.")
        record = Treatment(**values, recorded_by_id=principal.user_id)
    session.add(record)
    return await changed(session, principal, f"{record.__tablename__}.record", record)


async def list_clinical(
    session, principal, model, *, limit, cursor=None, due=False, animal_id=None
):
    statement = (
        select(model)
        .join(Animal, model.animal_id == Animal.id)
        .join(Farm)
        .join(Location, Farm.location_id == Location.id)
        .where(farm_scope(principal), Animal.deleted_at.is_(None), Farm.deleted_at.is_(None))
    )
    if animal_id:
        statement = statement.where(model.animal_id == animal_id)
    if due:
        newer = aliased(Vaccination)
        statement = statement.where(
            Vaccination.next_due_on <= date.today(),
            ~exists().where(ClinicalReversal.vaccination_id == Vaccination.id),
            ~select(newer.id)
            .where(
                newer.animal_id == Vaccination.animal_id,
                newer.vaccine_name == Vaccination.vaccine_name,
                or_(
                    newer.administered_on > Vaccination.administered_on,
                    (newer.administered_on == Vaccination.administered_on)
                    & (newer.id > Vaccination.id),
                ),
                ~select(ClinicalReversal.id)
                .where(ClinicalReversal.vaccination_id == newer.id)
                .exists(),
            )
            .exists(),
        )
    if cursor:
        statement = statement.where(model.id < cursor)
    rows = list((await session.scalars(statement.order_by(model.id.desc()).limit(limit + 1))).all())
    return {
        "data": [view(row) for row in rows[:limit]],
        "meta": {"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
        "error": None,
    }


async def clinical_detail(session, principal, model, record_id):
    record = await session.scalar(select(model).where(model.id == record_id))
    if record is None:
        raise ApiError(404, "NOT_FOUND", "Clinical record not found.")
    await animal_in_scope(session, principal, record.animal_id)
    data = view(record)
    target = (
        ClinicalReversal.vaccination_id if model is Vaccination else ClinicalReversal.treatment_id
    )
    reversal = await session.scalar(select(ClinicalReversal).where(target == record_id))
    data["reversal"] = view(reversal) if reversal else None
    return data


async def reverse_clinical(session, principal, model, record_id, reason):
    require_role(principal, "VETERINARIAN", "ADMIN")
    record = await session.scalar(select(model).where(model.id == record_id).with_for_update())
    if record is None:
        raise ApiError(404, "NOT_FOUND", "Clinical record not found.")
    await animal_in_scope(session, principal, record.animal_id)
    target_name = "vaccination_id" if model is Vaccination else "treatment_id"
    if await session.scalar(
        select(ClinicalReversal.id).where(getattr(ClinicalReversal, target_name) == record_id)
    ):
        raise ApiError(409, "CONFLICT", "The record has already been reversed.")
    reversal = ClinicalReversal(
        **{target_name: record_id}, actor_id=principal.user_id, reason=reason
    )
    session.add(reversal)
    return await changed(session, principal, f"{model.__tablename__}.reverse", reversal)
