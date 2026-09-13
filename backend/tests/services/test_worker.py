from uuid import uuid4

import httpx

from app.models.trust import OutboxEvent
from app.services.auth import CurrentPrincipal
from scripts.replay_outbox import replay
from scripts.worker import dispatch_one


async def test_worker_marks_success_only_after_acknowledged_delivery(session):
    actor = CurrentPrincipal(uuid4(), ("ADMIN",), None)
    event = OutboxEvent(topic="animal.created", aggregate_id=uuid4(), payload={"test": True})
    session.add(event)
    await session.commit()
    received = []

    def gateway(request):
        received.append(request)
        return httpx.Response(200, json={"accepted": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(gateway)) as client:
        assert await dispatch_one(session, actor, client, "https://gateway.test/events", "x" * 32)
    assert event.published_at is not None
    assert event.attempts == 1
    assert received[0].headers["Idempotency-Key"] == str(event.id)


async def test_worker_retains_failed_event_and_schedules_retry(session):
    actor = CurrentPrincipal(uuid4(), ("ADMIN",), None)
    event = OutboxEvent(topic="animal.created", aggregate_id=uuid4(), payload={})
    session.add(event)
    await session.commit()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    ) as client:
        assert await dispatch_one(session, actor, client, "https://gateway.test/events", "x" * 32)
        assert not await dispatch_one(
            session, actor, client, "https://gateway.test/events", "x" * 32
        )
    assert event.published_at is None
    assert event.attempts == 1
    assert event.next_attempt_at is not None
    assert event.last_error == "HTTPStatusError"


async def test_worker_dead_letters_and_operator_can_replay(session):
    actor = CurrentPrincipal(uuid4(), ("ADMIN",), None)
    event = OutboxEvent(topic="animal.created", aggregate_id=uuid4(), payload={}, attempts=29)
    session.add(event)
    await session.commit()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    ) as client:
        assert await dispatch_one(session, actor, client, "https://gateway.test/events", "x" * 32)
    assert event.attempts == 30
    assert event.dead_lettered_at is not None
    assert event.next_attempt_at is None
    assert not await dispatch_one(session, actor, client, "https://gateway.test/events", "x" * 32)
    assert await replay(session, event.id)
    assert event.attempts == 0
    assert event.dead_lettered_at is None
