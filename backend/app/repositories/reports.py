from uuid import UUID

from sqlalchemy import false, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import CaseReviewGrant
from app.models.reports import DiseaseReport, Farm


async def get_farm(session: AsyncSession, farm_id: UUID) -> Farm | None:
    return await session.scalar(select(Farm).where(Farm.id == farm_id, Farm.deleted_at.is_(None)))


async def get_report(session: AsyncSession, report_id: UUID) -> DiseaseReport | None:
    return await session.scalar(
        select(DiseaseReport).where(
            DiseaseReport.id == report_id,
            DiseaseReport.deleted_at.is_(None),
        )
    )


def _report_visibility_condition(
    *,
    user_id: UUID,
    roles: tuple[str, ...],
    location_path: str | None,
):
    role_set = set(roles)
    conditions = []
    if "ADMIN" in role_set:
        conditions.append(true())
    if "FARMER" in role_set:
        conditions.append(DiseaseReport.reporter_id == user_id)
    if role_set.intersection({"VETERINARIAN", "PARAVET"}) and location_path:
        conditions.append(DiseaseReport.location_path.startswith(location_path))
    if "DISTRICT_OFFICER" in role_set:
        conditions.append(
            select(CaseReviewGrant.id)
            .where(
                CaseReviewGrant.disease_report_id == DiseaseReport.id,
                CaseReviewGrant.grantee_id == user_id,
                CaseReviewGrant.revoked_at.is_(None),
                CaseReviewGrant.expires_at > func.now(),
            )
            .exists()
        )
    return or_(*conditions) if conditions else false()


async def get_visible_report(
    session: AsyncSession,
    report_id: UUID,
    *,
    user_id: UUID,
    roles: tuple[str, ...],
    location_path: str | None,
) -> DiseaseReport | None:
    return await session.scalar(
        select(DiseaseReport).where(
            DiseaseReport.id == report_id,
            DiseaseReport.deleted_at.is_(None),
            _report_visibility_condition(
                user_id=user_id,
                roles=roles,
                location_path=location_path,
            ),
        )
    )


async def list_visible_reports(
    session: AsyncSession,
    *,
    user_id: UUID,
    roles: tuple[str, ...],
    location_path: str | None,
    limit: int = 50,
) -> list[DiseaseReport]:
    statement = (
        select(DiseaseReport)
        .where(
            DiseaseReport.deleted_at.is_(None),
            _report_visibility_condition(
                user_id=user_id,
                roles=roles,
                location_path=location_path,
            ),
        )
        .order_by(DiseaseReport.created_at.desc(), DiseaseReport.id.desc())
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())
