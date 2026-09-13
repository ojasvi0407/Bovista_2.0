from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response, status

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.repositories.reports import get_visible_report, list_visible_reports
from app.schemas.reports import DiseaseReportCreate
from app.services.authorization import ForbiddenError
from app.services.reports import (
    InvalidReportError,
    ReportNotFoundError,
    VersionConflictError,
    _view,
    create_report,
    submit_report,
)
from app.services.trust import IdempotencyConflictError

router = APIRouter(prefix="/disease-reports", tags=["disease reports"])


def _version_from_etag(value: str) -> int:
    try:
        return int(value.strip().strip('"'))
    except ValueError as error:
        raise ApiError(
            400, "INVALID_IF_MATCH", "If-Match must contain a report version."
        ) from error


def _translate_report_error(error: Exception) -> ApiError:
    if isinstance(error, ReportNotFoundError):
        return ApiError(404, "REPORT_NOT_FOUND", str(error))
    if isinstance(error, ForbiddenError):
        return ApiError(403, "FORBIDDEN", str(error))
    if isinstance(error, (VersionConflictError, IdempotencyConflictError)):
        return ApiError(409, "CONFLICT", str(error))
    return ApiError(422, "INVALID_REPORT", str(error))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    payload: DiseaseReportCreate,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await create_report(session, principal, payload, idempotency_key)
        await session.commit()
        return envelope(result.data, meta={"idempotent_replay": result.replay})
    except (
        ReportNotFoundError,
        ForbiddenError,
        VersionConflictError,
        InvalidReportError,
        IdempotencyConflictError,
    ) as error:
        await session.rollback()
        raise _translate_report_error(error) from error


@router.post("/{report_id}/submit")
async def submit(
    report_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    if_match: Annotated[str, Header(alias="If-Match")],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await submit_report(
            session,
            principal,
            report_id,
            _version_from_etag(if_match),
            idempotency_key,
        )
        await session.commit()
        return envelope(result.data, meta={"idempotent_replay": result.replay})
    except (
        ReportNotFoundError,
        ForbiddenError,
        VersionConflictError,
        IdempotencyConflictError,
    ) as error:
        await session.rollback()
        raise _translate_report_error(error) from error


@router.get("/{report_id}")
async def get_one(
    report_id: UUID,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
) -> dict[str, Any]:
    report = await get_visible_report(
        session,
        report_id,
        user_id=principal.user_id,
        roles=principal.roles,
        location_path=principal.location_path,
    )
    if report is None:
        raise ApiError(404, "REPORT_NOT_FOUND", "Report not found.")
    response.headers["ETag"] = f'"{report.version}"'
    return envelope(_view(report))


@router.get("")
async def list_visible(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: UUID | None = None,
) -> dict[str, Any]:
    reports = await list_visible_reports(
        session,
        user_id=principal.user_id,
        roles=principal.roles,
        location_path=principal.location_path,
        limit=limit + 1,
        cursor=cursor,
    )
    return envelope(
        [_view(report) for report in reports[:limit]],
        meta={"next_cursor": str(reports[limit - 1].id) if len(reports) > limit else None},
    )
