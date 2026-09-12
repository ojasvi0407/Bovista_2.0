from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.schemas.decisions import RiskScoreView, TriageResultView
from app.services.authorization import ForbiddenError
from app.services.decisions import DecisionConfigurationError, DecisionService
from app.services.reports import InvalidReportError, ReportNotFoundError
from app.services.trust import IdempotencyConflictError

router = APIRouter(prefix="/disease-reports", tags=["decisions"])


def _decision_error(error: Exception) -> ApiError:
    if isinstance(error, ReportNotFoundError):
        return ApiError(404, "REPORT_NOT_FOUND", str(error))
    if isinstance(error, ForbiddenError):
        return ApiError(403, "FORBIDDEN", str(error))
    if isinstance(error, DecisionConfigurationError):
        return ApiError(503, "DECISION_RULES_UNAVAILABLE", str(error))
    return ApiError(409, "REPORT_NOT_SUBMITTED", str(error))


@router.post("/{report_id}/triage")
async def triage(
    report_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    """Return explainable candidates. Advisory only; veterinary assessment is required."""
    try:
        result = await DecisionService(session).triage(report_id, principal, idempotency_key)
        await session.commit()
        return envelope(
            TriageResultView.model_validate(result, from_attributes=True).model_dump(mode="json")
        )
    except (
        ReportNotFoundError,
        ForbiddenError,
        InvalidReportError,
        DecisionConfigurationError,
        IdempotencyConflictError,
    ) as error:
        await session.rollback()
        raise _decision_error(error) from error


@router.post("/{report_id}/risk-score")
async def risk_score(
    report_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await DecisionService(session).score_risk(report_id, principal, idempotency_key)
        await session.commit()
        return envelope(
            RiskScoreView.model_validate(result, from_attributes=True).model_dump(mode="json")
        )
    except (
        ReportNotFoundError,
        ForbiddenError,
        InvalidReportError,
        DecisionConfigurationError,
        IdempotencyConflictError,
    ) as error:
        await session.rollback()
        raise _decision_error(error) from error
