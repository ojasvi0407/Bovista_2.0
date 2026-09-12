from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.services.dashboard import (
    DashboardAccessError,
    DashboardFilterError,
    build_dashboard_summary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    date_from: date | None = None,
    date_to: date | None = None,
    species: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    disease_code: Annotated[str | None, Query(min_length=1, max_length=60)] = None,
    location_id: UUID | None = None,
    group_by: Literal["location", "species", "disease", "date"] = "location",
    location_level: Literal["STATE", "DISTRICT", "BLOCK", "VILLAGE"] | None = None,
) -> dict[str, Any]:
    try:
        data = await build_dashboard_summary(
            session,
            principal,
            date_from=date_from,
            date_to=date_to,
            species=species,
            disease_code=disease_code,
            location_id=location_id,
            group_by=group_by,
            location_level=location_level,
        )
        return envelope(data)
    except DashboardAccessError as error:
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except DashboardFilterError as error:
        raise ApiError(422, "INVALID_DASHBOARD_FILTER", str(error)) from error
