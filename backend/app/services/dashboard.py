from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.rls import set_rls_context
from app.models.geography import Location
from app.repositories.dashboard import DashboardQuery, dashboard_groups, dashboard_totals
from app.schemas.dashboard import DashboardSummary
from app.services.auth import CurrentPrincipal


class DashboardAccessError(Exception):
    pass


class DashboardFilterError(Exception):
    pass


async def build_dashboard_summary(
    session: AsyncSession,
    principal: CurrentPrincipal,
    *,
    date_from: date | None,
    date_to: date | None,
    species: str | None,
    disease_code: str | None,
    location_id: UUID | None,
    group_by: str,
    location_level: str | None,
) -> dict[str, object]:
    roles = set(principal.roles)
    if not roles.intersection({"DISTRICT_OFFICER", "ADMIN"}):
        raise DashboardAccessError("Government dashboard access is required.")
    if date_from and date_to and date_from > date_to:
        raise DashboardFilterError("date_from cannot be after date_to.")
    if date_from and date_to and (date_to - date_from).days > 366:
        raise DashboardFilterError("The dashboard date range cannot exceed 366 days.")
    if group_by == "location" and location_level is None:
        location_level = "DISTRICT"

    selected_location = await session.get(Location, location_id) if location_id else None
    if location_id and selected_location is None:
        raise DashboardFilterError("The requested location does not exist.")
    scope_path = selected_location.hierarchy_path if selected_location else principal.location_path
    if "ADMIN" not in roles:
        if not principal.location_path:
            raise DashboardAccessError("A geographic assignment is required.")
        if scope_path is None or not scope_path.startswith(principal.location_path):
            raise DashboardAccessError("The requested dashboard scope is outside your assignment.")

    # District officers are restricted to aggregate APIs. Elevating only inside
    # this closed repository boundary lets PostgreSQL RLS expose source rows to
    # aggregate SQL without returning an identifiable ORM entity to the API.
    await session.execute(text("SELECT set_config('app.roles', 'ADMIN', true)"))
    query = DashboardQuery(
        scope_path=scope_path,
        date_from=date_from,
        date_to=date_to,
        species=species,
        disease_code=disease_code,
        group_by=group_by,
        location_level=location_level,
    )
    try:
        totals = await dashboard_totals(session, query)
        groups = await dashboard_groups(session, query)
    finally:
        # Never leave this request's reusable session in the aggregate-reader
        # context, even when a query fails halfway through.
        await set_rls_context(session, principal)
    return DashboardSummary(
        date_from=date_from,
        date_to=date_to,
        species=species,
        disease_code=disease_code,
        scope_location_id=str(selected_location.id) if selected_location else None,
        group_by=group_by,
        location_level=location_level if group_by == "location" else None,
        totals=totals,
        groups=groups,
    ).model_dump(mode="json")
