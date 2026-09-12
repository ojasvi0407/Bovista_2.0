from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.clinical import Vaccination
from app.models.decisions import RiskScore, TriageResult
from app.models.geography import Location
from app.models.laboratory import LaboratorySample
from app.models.reports import Animal, DiseaseReport, Farm
from app.models.surveillance import Outbreak, VeterinaryCase


@dataclass(frozen=True, slots=True)
class DashboardQuery:
    scope_path: str | None
    date_from: date | None
    date_to: date | None
    species: str | None
    disease_code: str | None
    group_by: str
    location_level: str | None


def _latest_disease_code():
    return (
        select(TriageResult.suspected_diseases[0]["disease_code"].astext)
        .where(TriageResult.disease_report_id == DiseaseReport.id)
        .order_by(TriageResult.created_at.desc(), TriageResult.id.desc())
        .limit(1)
        .scalar_subquery()
    )


def _report_conditions(query: DashboardQuery):
    conditions = [
        DiseaseReport.deleted_at.is_(None),
        DiseaseReport.status == "SUBMITTED",
    ]
    if query.scope_path:
        conditions.append(DiseaseReport.location_path.startswith(query.scope_path))
    if query.date_from:
        conditions.append(DiseaseReport.onset_date >= query.date_from)
    if query.date_to:
        conditions.append(DiseaseReport.onset_date <= query.date_to)
    if query.species:
        conditions.append(DiseaseReport.species == query.species)
    if query.disease_code:
        conditions.append(_latest_disease_code() == query.disease_code)
    return conditions


def _animal_conditions(query: DashboardQuery):
    conditions = [Animal.deleted_at.is_(None), Farm.deleted_at.is_(None)]
    if query.scope_path:
        conditions.append(Location.hierarchy_path.startswith(query.scope_path))
    if query.species:
        conditions.append(Animal.species == query.species)
    return conditions


async def dashboard_totals(session: AsyncSession, query: DashboardQuery) -> dict[str, object]:
    report_count, mortality = (
        await session.execute(
            select(
                func.count(DiseaseReport.id),
                func.coalesce(func.sum(DiseaseReport.mortality_count), 0),
            ).where(*_report_conditions(query))
        )
    ).one()
    total_animals = await session.scalar(
        select(func.count(Animal.id))
        .join(Farm, Animal.farm_id == Farm.id)
        .join(Location, Farm.location_id == Location.id)
        .where(*_animal_conditions(query))
    )
    covered_animals = await session.scalar(
        select(func.count(distinct(Vaccination.animal_id)))
        .join(Animal, Vaccination.animal_id == Animal.id)
        .join(Farm, Animal.farm_id == Farm.id)
        .join(Location, Farm.location_id == Location.id)
        .where(
            *_animal_conditions(query),
            Vaccination.administered_on <= date.today(),
            Vaccination.next_due_on.is_not(None),
            Vaccination.next_due_on >= date.today(),
        )
    )
    active_cases = await session.scalar(
        select(func.count(distinct(VeterinaryCase.id)))
        .join(DiseaseReport, VeterinaryCase.disease_report_id == DiseaseReport.id)
        .where(VeterinaryCase.status != "CLOSED", *_report_conditions(query))
    )
    pending_samples = await session.scalar(
        select(func.count(distinct(LaboratorySample.id)))
        .join(DiseaseReport, LaboratorySample.disease_report_id == DiseaseReport.id)
        .where(
            LaboratorySample.status.in_({"REFERRED", "COLLECTED", "RECEIVED", "PROCESSING"}),
            *_report_conditions(query),
        )
    )
    high_risk_locations = await session.scalar(
        select(func.count(distinct(DiseaseReport.location_id)))
        .join(RiskScore, RiskScore.disease_report_id == DiseaseReport.id)
        .where(RiskScore.category.in_({"HIGH", "CRITICAL"}), *_report_conditions(query))
    )
    outbreak_conditions = [Outbreak.state.in_({"POTENTIAL", "DECLARED"})]
    if query.scope_path:
        outbreak_conditions.append(Location.hierarchy_path.startswith(query.scope_path))
    if query.disease_code:
        outbreak_conditions.append(Outbreak.disease_code == query.disease_code)
    active_outbreaks = await session.scalar(
        select(func.count(Outbreak.id))
        .join(Location, Outbreak.location_id == Location.id)
        .where(*outbreak_conditions)
    )
    animal_count = int(total_animals or 0)
    coverage = (
        (Decimal(int(covered_animals or 0)) * Decimal(100) / Decimal(animal_count)).quantize(
            Decimal("0.01")
        )
        if animal_count
        else Decimal("0.00")
    )
    return {
        "total_animals": animal_count,
        "active_cases": int(active_cases or 0),
        "disease_reports": int(report_count or 0),
        "mortality": int(mortality or 0),
        "vaccination_coverage_percent": coverage,
        "active_outbreaks": int(active_outbreaks or 0),
        "high_risk_locations": int(high_risk_locations or 0),
        "pending_laboratory_samples": int(pending_samples or 0),
    }


async def dashboard_groups(session: AsyncSession, query: DashboardQuery) -> list[dict[str, object]]:
    conditions = _report_conditions(query)
    if query.group_by == "species":
        key = DiseaseReport.species
        statement = select(
            key,
            func.count(DiseaseReport.id),
            func.coalesce(func.sum(DiseaseReport.mortality_count), 0),
        ).where(*conditions)
    elif query.group_by == "date":
        key = DiseaseReport.onset_date
        statement = select(
            key,
            func.count(DiseaseReport.id),
            func.coalesce(func.sum(DiseaseReport.mortality_count), 0),
        ).where(*conditions)
    elif query.group_by == "disease":
        key = func.coalesce(_latest_disease_code(), "UNKNOWN")
        statement = select(
            key,
            func.count(DiseaseReport.id),
            func.coalesce(func.sum(DiseaseReport.mortality_count), 0),
        ).where(*conditions)
    else:
        ancestor = aliased(Location)
        key = ancestor.code
        statement = (
            select(
                key,
                func.count(DiseaseReport.id),
                func.coalesce(func.sum(DiseaseReport.mortality_count), 0),
            )
            .join(ancestor, DiseaseReport.location_path.startswith(ancestor.hierarchy_path))
            .where(ancestor.level == query.location_level, *conditions)
        )
    rows = await session.execute(
        statement.group_by(key).order_by(func.count(DiseaseReport.id).desc(), key).limit(500)
    )
    return [
        {
            "key": item.isoformat() if isinstance(item, date) else str(item),
            "report_count": int(report_count),
            "mortality_count": int(mortality_count),
        }
        for item, report_count, mortality_count in rows
    ]
