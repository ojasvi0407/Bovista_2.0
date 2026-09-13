"""Controlled operator replay for a dead-lettered outbox event."""

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.db.session import async_session_factory, engine
from app.models.trust import OutboxEvent


async def replay(session, event_id: UUID) -> bool:
    event = await session.scalar(
        select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update()
    )
    if event is None or event.dead_lettered_at is None or event.published_at is not None:
        return False
    event.attempts = 0
    event.next_attempt_at = None
    event.dead_lettered_at = None
    event.last_error = None
    await session.flush()
    return True


async def run(event_id: UUID) -> None:
    try:
        async with async_session_factory() as session, session.begin():
            if not await replay(session, event_id):
                raise SystemExit("Event is not an unpublished dead-lettered event.")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset one reviewed dead-lettered event for delivery."
    )
    parser.add_argument("event_id", type=UUID)
    args = parser.parse_args()
    confirmation = input(f"Replay outbox event {args.event_id}? Type REPLAY: ")
    if confirmation != "REPLAY":
        raise SystemExit("Replay cancelled.")
    asyncio.run(run(args.event_id))


if __name__ == "__main__":
    main()
