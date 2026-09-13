from uuid import UUID

from sqlalchemy import exists, false, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.models.geography import Location
from app.models.identity import CaseReviewGrant
from app.models.reports import Animal, DiseaseReport, Farm
from app.services.auth import CurrentPrincipal


def farm_scope(principal: CurrentPrincipal):
    if "ADMIN" in principal.roles:
        return true()
    if "FARMER" in principal.roles:
        return Farm.owner_id == principal.user_id
    if set(principal.roles) & {"VETERINARIAN", "PARAVET"} and principal.location_path:
        return Location.hierarchy_path.startswith(principal.location_path)
    return false()


def report_scope(principal: CurrentPrincipal, *, lab: bool = False, write: bool = False):
    if "ADMIN" in principal.roles:
        return true()
    if "FARMER" in principal.roles:
        return DiseaseReport.reporter_id == principal.user_id
    roles = {"VETERINARIAN", "PARAVET"}
    if lab:
        roles.add("LAB_TECHNICIAN")
    if set(principal.roles) & roles and principal.location_path:
        return DiseaseReport.location_path.startswith(principal.location_path)
    if "DISTRICT_OFFICER" in principal.roles and not write:
        return exists().where(
            CaseReviewGrant.disease_report_id == DiseaseReport.id,
            CaseReviewGrant.grantee_id == principal.user_id,
            CaseReviewGrant.revoked_at.is_(None),
            CaseReviewGrant.expires_at > func.now(),
        )
    return false()


async def animal_in_scope(
    session: AsyncSession, principal: CurrentPrincipal, animal_id: UUID, *, lock: bool = False
):
    statement = (
        select(Animal)
        .join(Farm)
        .join(Location, Farm.location_id == Location.id)
        .where(
            Animal.id == animal_id,
            Animal.deleted_at.is_(None),
            Farm.deleted_at.is_(None),
            farm_scope(principal),
        )
    )
    if lock:
        statement = statement.with_for_update(of=(Farm, Animal))
    animal = await session.scalar(statement)
    if animal is None:
        raise ApiError(404, "ANIMAL_NOT_FOUND", "Animal not found.")
    return animal


async def report_in_scope(
    session: AsyncSession, principal: CurrentPrincipal, report_id: UUID, *, write: bool = False
):
    statement = select(DiseaseReport).where(
        DiseaseReport.id == report_id,
        DiseaseReport.deleted_at.is_(None),
        report_scope(principal, lab=True, write=write),
    )
    if write:
        statement = statement.with_for_update()
    report = await session.scalar(statement)
    if report is None:
        raise ApiError(404, "REPORT_NOT_FOUND", "Report not found.")
    return report
