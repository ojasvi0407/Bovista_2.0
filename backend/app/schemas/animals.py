from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnimalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    farm_id: UUID
    herd_id: UUID | None = None
    species: str = Field(min_length=1, max_length=40)
    tag_number: str | None = Field(default=None, min_length=1, max_length=100)
    sex: str | None = Field(default=None, min_length=1, max_length=16)
    birth_date: date | None = None

    @model_validator(mode="after")
    def valid_birth_date(self):
        if self.birth_date and self.birth_date > date.today():
            raise ValueError("Birth date cannot be in the future.")
        return self


class AnimalView(BaseModel):
    id: UUID
    farm_id: UUID
    herd_id: UUID | None
    species: str
    tag_number: str | None
    sex: str | None
    birth_date: date | None
    version: int


class AnimalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    tag_number: str | None = Field(default=None, min_length=1, max_length=100)
    sex: str | None = Field(default=None, min_length=1, max_length=16)
    birth_date: date | None = None

    @model_validator(mode="after")
    def valid_changes(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one change.")
        if self.birth_date and self.birth_date > date.today():
            raise ValueError("Birth date cannot be in the future.")
        return self
