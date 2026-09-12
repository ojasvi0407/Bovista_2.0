from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.trust import AuditLog, IdempotencyReceipt, OutboxEvent
from app.services.trust import claim_idempotency, enqueue_event, record_audit


@pytest.mark.asyncio
async def test_mutation_audit_and_outbox_commit_together(session) -> None:
    actor_id = uuid4()
    report_id = uuid4()

    async with session.begin():
        claim = await claim_idempotency(
            session,
            actor_id=actor_id,
            key="report-001",
            request_hash="sha256:req",
        )
        await record_audit(
            session,
            actor_id=actor_id,
            action="report.create",
            resource_type="report",
            resource_id=report_id,
            success=True,
        )
        await enqueue_event(
            session,
            topic="report.created",
            aggregate_id=report_id,
            payload={"id": str(report_id)},
        )

    assert claim.is_replay is False
    assert await session.scalar(select(func.count(AuditLog.id))) == 1
    assert await session.scalar(select(func.count(OutboxEvent.id))) == 1


@pytest.mark.asyncio
async def test_idempotency_replay_returns_original_result(session) -> None:
    actor_id = uuid4()

    async with session.begin():
        first = await claim_idempotency(
            session,
            actor_id=actor_id,
            key="same-key",
            request_hash="sha256:req",
        )
        await first.store_response(status_code=201, body={"id": "server-id"})

    async with session.begin():
        second = await claim_idempotency(
            session,
            actor_id=actor_id,
            key="same-key",
            request_hash="sha256:req",
        )

    assert second.is_replay is True
    assert second.response_status == 201
    assert second.response_body == {"id": "server-id"}
    assert await session.scalar(select(func.count(IdempotencyReceipt.id))) == 1


@pytest.mark.asyncio
async def test_audit_entries_form_a_hash_chain(session) -> None:
    actor_id = uuid4()

    async with session.begin():
        first = await record_audit(
            session,
            actor_id=actor_id,
            action="report.create",
            resource_type="report",
            resource_id=uuid4(),
            success=True,
        )
        second = await record_audit(
            session,
            actor_id=actor_id,
            action="report.submit",
            resource_type="report",
            resource_id=uuid4(),
            success=True,
        )

    assert first.previous_hash is None
    assert second.previous_hash == first.entry_hash
    assert len(first.entry_hash) == 64
    assert len(second.entry_hash) == 64
