from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReportedSymptom(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    observed_at: datetime | None = None


class DiseaseReportCreate(BaseModel):
    client_generated_id: UUID
    farm_id: UUID
    animal_id: UUID | None = None
    herd_id: UUID | None = None
    species: str = Field(min_length=1, max_length=40)
    symptoms: list[ReportedSymptom] = Field(min_length=1, max_length=50)
    affected_count: int = Field(ge=1)
    mortality_count: int = Field(ge=0)
    onset_date: date
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    vaccination: dict[str, object] | None = None
    treatment: dict[str, object] | None = None
    environment: dict[str, object] | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_counts(self) -> "DiseaseReportCreate":
        if self.mortality_count > self.affected_count:
            raise ValueError("mortality_count cannot exceed affected_count")
        return self


class DiseaseReportView(BaseModel):
    id: UUID
    status: str
    version: int
    farm_id: UUID
    species: str
    affected_count: int
    mortality_count: int
    onset_date: date
    submitted_at: datetime | None
