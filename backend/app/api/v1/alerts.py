from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.repositories.alerts import InvalidAlertCursorError, list_visible_alerts
from app.services.alerts import (
    AlertConflictError,
    AlertNotFoundError,
    acknowledge_alert,
    alert_view,
)
from app.services.trust import IdempotencyConflictError

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    status: Literal["ACTIVE", "ACKNOWLEDGED", "CLOSED"] | None = None,
) -> dict[str, Any]:
    try:
        page = await list_visible_alerts(
            session,
            user_id=principal.user_id,
            roles=principal.roles,
            limit=limit,
            cursor=cursor,
            status=status,
        )
    except InvalidAlertCursorError as error:
        raise ApiError(400, "INVALID_CURSOR", str(error)) from error
    return envelope(
        [alert_view(item) for item in page.items],
        meta={"next_cursor": page.next_cursor},
    )


@router.post("/{alert_id}/acknowledge")
async def acknowledge(
    alert_id: UUID,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> dict[str, Any]:
    try:
        result = await acknowledge_alert(
            session,
            alert_id=alert_id,
            principal=principal,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return envelope(result.data, meta={"idempotent_replay": result.replay})
    except AlertNotFoundError as error:
        await session.rollback()
        raise ApiError(404, "ALERT_NOT_FOUND", str(error)) from error
    except (AlertConflictError, IdempotencyConflictError) as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error
