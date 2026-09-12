from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class AnimalCreate(BaseModel):
    farm_id: UUID
    species: str = Field(min_length=1, max_length=40)
    tag_number: str | None = Field(default=None, min_length=1, max_length=100)
    sex: str | None = Field(default=None, min_length=1, max_length=16)
    birth_date: date | None = None


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
    tag_number: str | None = Field(default=None, min_length=1, max_length=100)
    sex: str | None = Field(default=None, min_length=1, max_length=16)
    birth_date: date | None = None
