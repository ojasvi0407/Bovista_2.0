from typing import Protocol
from uuid import UUID

from app.services.auth import CurrentPrincipal


class ForbiddenError(Exception):
    pass


class ScopedResource(Protocol):
    reporter_id: UUID
    location_path: str


def _inside_assignment(resource_path: str, assignment_path: str | None) -> bool:
    return bool(assignment_path and resource_path.startswith(assignment_path))


def authorize(principal: CurrentPrincipal, action: str, resource: ScopedResource) -> None:
    roles = set(principal.roles)
    if "ADMIN" in roles:
        return
    if action == "report.read_aggregate" and "DISTRICT_OFFICER" in roles:
        return
    if action in {"report.read", "report.read_identifiable"}:
        if "FARMER" in roles and resource.reporter_id == principal.user_id:
            return
        if roles.intersection({"VETERINARIAN", "PARAVET"}) and _inside_assignment(
            resource.location_path, principal.location_path
        ):
            return
        grants = getattr(resource, "active_review_grantee_ids", ())
        if "DISTRICT_OFFICER" in roles and principal.user_id in grants:
            return
    raise ForbiddenError(f"Action {action!r} is not permitted for this resource.")
