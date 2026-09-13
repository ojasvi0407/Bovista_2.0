"""Durable outbox dispatcher with bounded retries and idempotent gateway delivery."""

import asyncio
import logging
import os
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.db.base import utc_now
from app.db.rls import set_rls_context
from app.db.session import async_session_factory, engine
from app.models.identity import Role, User, UserRole
from app.models.trust import OutboxEvent
from app.services.auth import CurrentPrincipal
from app.services.outbreaks import analyze_seed_report

logger = logging.getLogger(__name__)


def validate_gateway(url, token):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("EVENT_DELIVERY_URL must be an HTTPS gateway without URL credentials.")
    if len(token) < 32:
        raise ValueError("EVENT_DELIVERY_TOKEN must contain at least 32 characters.")


async def deliver_event(session, event, principal, client, url, token):
    if event.topic == "outbreak.analysis.requested":
        await analyze_seed_report(
            session,
            seed_report_id=event.aggregate_id,
            principal=principal,
            idempotency_key=f"worker:{event.id}",
            settings=get_settings(),
        )
        return
    response = await client.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": str(event.id),
        },
        json={
            "event_id": str(event.id),
            "topic": event.topic,
            "aggregate_id": str(event.aggregate_id),
            "payload": event.payload,
        },
    )
    response.raise_for_status()


async def dispatch_one(session, principal, client, url, token):
    await set_rls_context(session, principal)
    event = await session.scalar(
        select(OutboxEvent)
        .where(
            OutboxEvent.published_at.is_(None),
            OutboxEvent.dead_lettered_at.is_(None),
            OutboxEvent.attempts < 30,
            or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= utc_now()),
        )
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if event is None:
        return False
    event.attempts += 1
    try:
        # A failed domain action cannot leave partial data or poison the retry transaction.
        async with session.begin_nested():
            await deliver_event(session, event, principal, client, url, token)
    except Exception as error:
        event.last_error = type(error).__name__
        if event.attempts >= 30:
            event.dead_lettered_at = utc_now()
            event.next_attempt_at = None
            logger.critical(
                "Outbox event dead-lettered (event_id=%s, type=%s)",
                event.id,
                event.last_error,
            )
        else:
            event.next_attempt_at = utc_now() + timedelta(seconds=min(3600, 2**event.attempts))
            logger.warning(
                "Outbox delivery deferred (event_id=%s, type=%s)",
                event.id,
                event.last_error,
            )
    else:
        event.published_at = utc_now()
        event.next_attempt_at = None
        event.last_error = None
    await session.flush()
    return True


async def run():
    url = os.environ.get("EVENT_DELIVERY_URL", "")
    token = os.environ.get("EVENT_DELIVERY_TOKEN", "")
    validate_gateway(url, token)
    user_id = UUID(os.environ["WORKER_USER_ID"])
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            while True:
                async with async_session_factory() as session, session.begin():
                    admin = await session.scalar(
                        select(User.id)
                        .join(UserRole)
                        .join(Role)
                        .where(User.id == user_id, User.is_active.is_(True), Role.code == "ADMIN")
                    )
                    if admin is None:
                        raise RuntimeError(
                            "WORKER_USER_ID must identify an active admin service account."
                        )
                    principal = CurrentPrincipal(user_id, ("ADMIN",), None)
                    handled = await dispatch_one(session, principal, client, url, token)
                if not handled:
                    await asyncio.sleep(2)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
