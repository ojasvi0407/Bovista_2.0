import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import false, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reports import DiseaseReport
from app.models.surveillance import Alert


class InvalidAlertCursorError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AlertPage:
    items: list[Alert]
    next_cursor: str | None


def _visibility_condition(user_id: UUID, roles: tuple[str, ...]):
    conditions = [Alert.recipient_id == user_id]
    if "FARMER" in roles:
        conditions.append(
            select(DiseaseReport.id)
            .where(
                DiseaseReport.id == Alert.disease_report_id,
                DiseaseReport.reporter_id == user_id,
            )
            .exists()
        )
    if "ADMIN" in roles:
        conditions.append(true())
    return or_(*conditions) if conditions else false()


def _encode_cursor(alert: Alert) -> str:
    payload = json.dumps(
        {"created_at": alert.created_at.isoformat(), "id": str(alert.id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            raise ValueError("cursor timestamp must include a timezone")
        return created_at, UUID(payload["id"])
    except (binascii.Error, KeyError, TypeError, ValueError) as error:
        raise InvalidAlertCursorError("The alert cursor is invalid.") from error


async def list_visible_alerts(
    session: AsyncSession,
    *,
    user_id: UUID,
    roles: tuple[str, ...],
    limit: int,
    cursor: str | None,
    status: str | None,
) -> AlertPage:
    statement = select(Alert).where(_visibility_condition(user_id, roles))
    if status is not None:
        statement = statement.where(Alert.status == status)
    if cursor:
        created_at, alert_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                Alert.created_at < created_at,
                (Alert.created_at == created_at) & (Alert.id < alert_id),
            )
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit + 1)
            )
        ).all()
    )
    has_more = len(rows) > limit
    items = rows[:limit]
    return AlertPage(
        items=items,
        next_cursor=_encode_cursor(items[-1]) if has_more and items else None,
    )


async def get_visible_alert_for_update(
    session: AsyncSession,
    alert_id: UUID,
    *,
    user_id: UUID,
    roles: tuple[str, ...],
) -> Alert | None:
    return await session.scalar(
        select(Alert)
        .where(
            Alert.id == alert_id,
            _visibility_condition(user_id, roles),
        )
        .with_for_update()
    )
