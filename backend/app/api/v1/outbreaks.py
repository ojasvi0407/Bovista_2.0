from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.core.config import Settings, get_settings
from app.repositories.surveillance import get_outbreak, list_outbreaks
from app.schemas.outbreaks import (
    OutbreakAnalyzeRequest,
    OutbreakTransitionRequest,
    OutbreakView,
)
from app.services.authorization import ForbiddenError
from app.services.outbreaks import (
    OutbreakConflictError,
    OutbreakNotFoundError,
    analyze_seed_report,
    transition_outbreak,
)
from app.services.trust import IdempotencyConflictError

router = APIRouter(prefix="/outbreaks", tags=["outbreaks"])


def _view(outbreak) -> dict[str, object]:
    return OutbreakView.model_validate(outbreak, from_attributes=True).model_dump(mode="json")


@router.post("/analyze")
async def analyze(
    payload: OutbreakAnalyzeRequest,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    if not set(principal.roles).intersection({"VETERINARIAN", "PARAVET", "ADMIN"}):
        raise ApiError(403, "FORBIDDEN", "Clinical staff access is required.")
    try:
        outbreak = await analyze_seed_report(
            session,
            seed_report_id=payload.seed_report_id,
            principal=principal,
            idempotency_key=idempotency_key,
            settings=settings,
        )
        await session.commit()
        return envelope(
            {
                "detected": outbreak is not None,
                "outbreak": _view(outbreak) if outbreak else None,
            }
        )
    except OutbreakNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "REPORT_NOT_FOUND", str(error)) from error
    except ForbiddenError as error:
        await session.rollback()
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except (OutbreakConflictError, IdempotencyConflictError) as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error


@router.get("")
async def list_all(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
) -> dict[str, Any]:
    del principal
    return envelope([_view(item) for item in await list_outbreaks(session)])


@router.get("/{outbreak_id}")
async def get_one(
    outbreak_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
) -> dict[str, Any]:
    del principal
    outbreak = await get_outbreak(session, outbreak_id)
    if outbreak is None:
        raise ApiError(404, "OUTBREAK_NOT_FOUND", "Outbreak not found.")
    return envelope(_view(outbreak))


async def _transition(
    outbreak_id: UUID,
    target_state: str,
    payload: OutbreakTransitionRequest,
    principal,
    session: AsyncSession,
    idempotency_key: str,
) -> dict[str, Any]:
    try:
        outbreak = await transition_outbreak(
            session,
            outbreak_id=outbreak_id,
            target_state=target_state,
            reason=payload.reason,
            principal=principal,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return envelope(_view(outbreak))
    except OutbreakNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "OUTBREAK_NOT_FOUND", str(error)) from error
    except ForbiddenError as error:
        await session.rollback()
        raise ApiError(403, "FORBIDDEN", str(error)) from error
    except (OutbreakConflictError, IdempotencyConflictError) as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error


@router.post("/{outbreak_id}/declare")
async def declare(
    outbreak_id: UUID,
    payload: OutbreakTransitionRequest,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    return await _transition(outbreak_id, "DECLARED", payload, principal, session, idempotency_key)


@router.post("/{outbreak_id}/dismiss")
async def dismiss(
    outbreak_id: UUID,
    payload: OutbreakTransitionRequest,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    return await _transition(outbreak_id, "DISMISSED", payload, principal, session, idempotency_key)
