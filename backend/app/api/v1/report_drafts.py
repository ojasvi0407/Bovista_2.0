from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Response
from pydantic import Field
from sqlalchemy import select

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.v1.clinical import Key
from app.api.v1.farms import version_number
from app.db.base import utc_now
from app.models.reports import DiseaseReport
from app.repositories.operations import report_scope
from app.schemas.operations import StrictInput
from app.services.operation_commands import changed, command, require_role
from app.services.reports import _view

router = APIRouter(prefix="/disease-reports", tags=["disease reports"])


class DraftUpdate(StrictInput):
    affected_count: int = Field(ge=1)
    mortality_count: int = Field(ge=0)
    onset_date: date
    notes: str | None = Field(default=None, max_length=4000)


async def modify(session, principal, report_id, version, payload=None):
    report = await session.scalar(
        select(DiseaseReport)
        .where(
            DiseaseReport.id == report_id,
            DiseaseReport.deleted_at.is_(None),
            report_scope(principal),
        )
        .with_for_update()
    )
    if report is None:
        raise ApiError(404, "REPORT_NOT_FOUND", "Report not found.")
    if report.status != "DRAFT" or report.version != version:
        raise ApiError(409, "CONFLICT", "Only a draft with the current version can be changed.")
    if payload:
        if payload.mortality_count > payload.affected_count or payload.onset_date > date.today():
            raise ApiError(422, "INVALID_REPORT", "Clinical counts or onset date are invalid.")
        for field, value in payload.model_dump().items():
            setattr(report, field, value)
    else:
        report.deleted_at = utc_now()
    report.version += 1
    await changed(session, principal, "report.update" if payload else "report.archive", report)
    return _view(report)


@router.put("/{report_id}")
async def draft_update(
    report_id: UUID,
    payload: DraftUpdate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Annotated[str, Header(alias="If-Match")],
):
    require_role(principal, "FARMER", "VETERINARIAN", "PARAVET", "ADMIN")
    version = version_number(if_match)
    return await command(
        session,
        principal,
        idempotency_key,
        "report.update",
        {"id": str(report_id), "version": version, **payload.model_dump(mode="json")},
        lambda: modify(session, principal, report_id, version, payload),
    )


@router.delete("/{report_id}", status_code=204)
async def draft_archive(
    report_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
    if_match: Annotated[str, Header(alias="If-Match")],
):
    require_role(principal, "FARMER", "VETERINARIAN", "PARAVET", "ADMIN")
    version = version_number(if_match)
    await command(
        session,
        principal,
        idempotency_key,
        "report.archive",
        {"id": str(report_id), "version": version},
        lambda: modify(session, principal, report_id, version),
    )
    return Response(status_code=204)
