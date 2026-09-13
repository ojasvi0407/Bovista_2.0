from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VaccinationCreate(StrictInput):
    animal_id: UUID
    vaccine_name: Name
    batch_number: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    administered_on: date
    next_due_on: date | None = None

    @model_validator(mode="after")
    def dates_valid(self):
        if self.administered_on > date.today():
            raise ValueError("Administration date cannot be in the future.")
        if self.next_due_on and self.next_due_on < self.administered_on:
            raise ValueError("Next due date cannot precede administration.")
        return self


class TreatmentCreate(StrictInput):
    animal_id: UUID
    case_id: UUID
    medicine_name: Name
    dosage: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    dosage_unit: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
    ]
    duration_days: int = Field(ge=1, le=365)
    administered_on: date

    @model_validator(mode="after")
    def date_valid(self):
        if self.administered_on > date.today():
            raise ValueError("Administration date cannot be in the future.")
        return self


class ReasonCommand(StrictInput):
    reason: Reason


class SampleCreate(StrictInput):
    disease_report_id: UUID
    specimen_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    lab_reference: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ] = None


class ResultCreate(StrictInput):
    disease_code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ]
    outcome: Literal["POSITIVE", "NEGATIVE", "INCONCLUSIVE"]
    findings: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]


class FarmCreate(StrictInput):
    location_id: UUID
    name: Name


class FarmUpdate(StrictInput):
    name: Name


class HerdCreate(StrictInput):
    farm_id: UUID
    name: Name
    species: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    animal_count: int = Field(ge=0, le=1000000)


class HerdUpdate(StrictInput):
    name: Name | None = None
    animal_count: int | None = Field(default=None, ge=0, le=1000000)

    @model_validator(mode="after")
    def non_null_changes(self):
        if not self.model_fields_set or any(
            getattr(self, f) is None for f in self.model_fields_set
        ):
            raise ValueError("Provide at least one non-null field.")
        return self
