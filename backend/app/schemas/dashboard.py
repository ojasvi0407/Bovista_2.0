from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardTotals(BaseModel):
    total_animals: int
    active_cases: int
    disease_reports: int
    mortality: int
    vaccination_coverage_percent: Decimal
    active_outbreaks: int
    high_risk_locations: int
    pending_laboratory_samples: int


class DashboardGroup(BaseModel):
    key: str
    report_count: int
    mortality_count: int


class DashboardSummary(BaseModel):
    date_from: date | None
    date_to: date | None
    species: str | None
    disease_code: str | None
    scope_location_id: str | None
    group_by: str
    location_level: str | None
    totals: DashboardTotals
    groups: list[DashboardGroup]
