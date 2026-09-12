from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class TriageResultView(BaseModel):
    id: UUID
    rule_pack_version: str
    suspected_diseases: list[dict[str, object]]
    contributing_factors: list[str]
    missing_fields: list[str]
    recommended_actions: list[str]
    data_confidence: Decimal
    disclaimer: str
    created_at: datetime


class RiskScoreView(BaseModel):
    id: UUID
    rule_pack_version: str
    value: int
    category: str
    data_confidence: Decimal
    missing_signals: list[str]
    created_at: datetime
