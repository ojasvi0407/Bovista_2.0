import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utc_now, uuid7
from app.models.trust import AuditLog, IdempotencyReceipt, OutboxEvent


class IdempotencyConflictError(Exception):
    pass


@dataclass(slots=True)
class IdempotencyClaim:
    session: AsyncSession
    receipt: IdempotencyReceipt
    is_replay: bool

    @property
    def response_status(self) -> int | None:
        return self.receipt.response_status

    @property
    def response_body(self) -> dict[str, Any] | None:
        return self.receipt.response_body

    async def store_response(self, status_code: int, body: dict[str, Any]) -> None:
        self.receipt.response_status = status_code
        self.receipt.response_body = body
        await self.session.flush()


async def claim_idempotency(
    session: AsyncSession,
    actor_id: UUID,
    key: str,
    request_hash: str,
) -> IdempotencyClaim:
    now = utc_now()
    inserted_id = await session.scalar(
        insert(IdempotencyReceipt)
        .values(
            id=uuid7(),
            actor_id=actor_id,
            idempotency_key=key,
            request_hash=request_hash,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_idempotency_actor_key")
        .returning(IdempotencyReceipt.id)
    )
    receipt = await session.scalar(
        select(IdempotencyReceipt)
        .where(
            IdempotencyReceipt.actor_id == actor_id,
            IdempotencyReceipt.idempotency_key == key,
        )
        .with_for_update()
    )
    if receipt is None:
        raise RuntimeError("Idempotency receipt could not be claimed.")
    if receipt.request_hash != request_hash:
        raise IdempotencyConflictError("Idempotency key was used for another request.")
    return IdempotencyClaim(
        session=session,
        receipt=receipt,
        is_replay=inserted_id is None,
    )


async def record_audit(
    session: AsyncSession,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    success: bool,
    request_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    await session.execute(text("SELECT pg_advisory_xact_lock(118974221)"))
    previous_hash = await session.scalar(
        select(AuditLog.entry_hash)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .limit(1)
    )
    occurred_at = utc_now()
    canonical_entry = json.dumps(
        {
            "actor_id": str(actor_id) if actor_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "occurred_at": occurred_at.isoformat(),
            "request_metadata": request_metadata or {},
            "success": success,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    chain_payload = f"{previous_hash or ''}{canonical_entry}".encode()
    key = get_settings().audit_hmac_key.get_secret_value().encode()
    entry_hash = hmac.new(key, chain_payload, hashlib.sha256).hexdigest()
    audit = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        occurred_at=occurred_at,
        request_metadata=request_metadata or {},
        success=success,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    session.add(audit)
    await session.flush()
    return audit


async def enqueue_event(
    session: AsyncSession,
    topic: str,
    aggregate_id: UUID,
    payload: dict[str, Any],
) -> OutboxEvent:
    event = OutboxEvent(topic=topic, aggregate_id=aggregate_id, payload=payload)
    session.add(event)
    await session.flush()
    return event
