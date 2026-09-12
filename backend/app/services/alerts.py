import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.repositories.alerts import get_visible_alert_for_update
from app.schemas.alerts import AlertView
from app.services.auth import CurrentPrincipal
from app.services.trust import claim_idempotency, enqueue_event, record_audit


class AlertNotFoundError(Exception):
    pass


class AlertConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AlertMutationResult:
    data: dict[str, object]
    replay: bool = False


def alert_view(alert) -> dict[str, object]:
    return AlertView.model_validate(alert, from_attributes=True).model_dump(mode="json")


async def acknowledge_alert(
    session: AsyncSession,
    *,
    alert_id: UUID,
    principal: CurrentPrincipal,
    idempotency_key: str,
) -> AlertMutationResult:
    alert = await get_visible_alert_for_update(
        session,
        alert_id,
        user_id=principal.user_id,
        roles=principal.roles,
    )
    if alert is None:
        raise AlertNotFoundError("Alert not found.")
    request_hash = hashlib.sha256(f"acknowledge:{alert_id}".encode()).hexdigest()
    claim = await claim_idempotency(
        session,
        principal.user_id,
        idempotency_key,
        request_hash,
    )
    if claim.is_replay:
        if claim.response_body is None:
            raise AlertConflictError("The original request is still being processed.")
        return AlertMutationResult(claim.response_body, replay=True)
    if alert.status != "ACTIVE":
        raise AlertConflictError("Only an active alert can be acknowledged.")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = utc_now()
    alert.acknowledged_by_id = principal.user_id
    data = alert_view(alert)
    await record_audit(
        session,
        principal.user_id,
        "alert.acknowledge",
        "alert",
        alert.id,
        True,
    )
    await enqueue_event(
        session,
        "alert.acknowledged",
        alert.id,
        {"id": str(alert.id), "acknowledged_by_id": str(principal.user_id)},
    )
    await claim.store_response(200, data)
    await session.flush()
    return AlertMutationResult(data)
