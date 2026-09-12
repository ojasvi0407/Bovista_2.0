from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OutbreakAnalyzeRequest(BaseModel):
    seed_report_id: UUID


class OutbreakTransitionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class OutbreakView(BaseModel):
    id: UUID
    location_id: UUID
    disease_code: str
    state: str
    config_version: str
    score: Decimal
    factors: list[dict[str, object]]
    declared_by_id: UUID | None
    declared_at: datetime | None
    decision_reason: str | None
