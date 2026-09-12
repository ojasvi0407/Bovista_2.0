from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertView(BaseModel):
    id: UUID
    disease_report_id: UUID
    alert_type: str
    severity: str
    status: str
    message: str
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_id: UUID | None
