from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decisions import TriageResult
from app.models.reports import DiseaseReport
from app.models.surveillance import Outbreak


async def get_outbreak(session: AsyncSession, outbreak_id: UUID) -> Outbreak | None:
    return await session.get(Outbreak, outbreak_id)


async def list_outbreaks(session: AsyncSession, *, limit: int = 50) -> list[Outbreak]:
    return list(
        (
            await session.scalars(
                select(Outbreak)
                .order_by(Outbreak.created_at.desc(), Outbreak.id.desc())
                .limit(limit)
            )
        ).all()
    )


async def latest_triage_disease(session: AsyncSession, report_id: UUID) -> str | None:
    result = await session.scalar(
        select(TriageResult)
        .where(TriageResult.disease_report_id == report_id)
        .order_by(TriageResult.created_at.desc())
        .limit(1)
    )
    if result is None or not result.suspected_diseases:
        return None
    value = result.suspected_diseases[0].get("disease_code")
    return str(value) if value else None


async def latest_triage_diseases(session: AsyncSession, report_ids: list[UUID]) -> dict[UUID, str]:
    if not report_ids:
        return {}
    rows = await session.execute(
        select(
            TriageResult.disease_report_id,
            TriageResult.suspected_diseases,
        )
        .where(TriageResult.disease_report_id.in_(report_ids))
        .distinct(TriageResult.disease_report_id)
        .order_by(
            TriageResult.disease_report_id,
            TriageResult.created_at.desc(),
            TriageResult.id.desc(),
        )
    )
    result: dict[UUID, str] = {}
    for report_id, suspected_diseases in rows:
        if suspected_diseases:
            value = suspected_diseases[0].get("disease_code")
            if value:
                result[report_id] = str(value)
    return result


async def nearby_submitted_reports(
    session: AsyncSession,
    seed: DiseaseReport,
    *,
    radius_meters: int,
    earliest_onset,
    limit: int = 500,
) -> list[tuple[DiseaseReport, float, float]]:
    rows = await session.execute(
        select(
            DiseaseReport,
            func.ST_Y(DiseaseReport.report_geometry).label("latitude"),
            func.ST_X(DiseaseReport.report_geometry).label("longitude"),
        )
        .where(
            DiseaseReport.status == "SUBMITTED",
            DiseaseReport.onset_date >= earliest_onset,
            func.ST_DWithin(
                cast(DiseaseReport.report_geometry, Geography),
                cast(seed.report_geometry, Geography),
                radius_meters,
            ),
        )
        .order_by(DiseaseReport.onset_date.desc(), DiseaseReport.id)
        .limit(limit)
    )
    return [(row[0], float(row[1]), float(row[2])) for row in rows.all()]
