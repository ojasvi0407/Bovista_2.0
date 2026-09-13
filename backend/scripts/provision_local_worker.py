"""Provision the fixed local-development identity used by the outbox worker."""

import asyncio
import os
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.identity import Role, User, UserRole
from scripts.database_url import normalize_postgres_url


async def provision(session: AsyncSession, *, worker_id: UUID) -> None:
    worker = await session.get(User, worker_id)
    if worker is None:
        worker = User(
            id=worker_id,
            user_type="STAFF",
            staff_identifier="local-outbox-worker",
            display_name="Local Outbox Worker",
            is_active=True,
        )
        session.add(worker)
        await session.flush()
    elif worker.staff_identifier != "local-outbox-worker":
        raise RuntimeError("WORKER_USER_ID already belongs to a different user.")
    else:
        worker.is_active = True

    admin_role = await session.scalar(select(Role).where(Role.code == "ADMIN"))
    if admin_role is None:
        admin_role = Role(code="ADMIN", description="System administrator")
        session.add(admin_role)
        await session.flush()

    if await session.get(UserRole, (worker_id, admin_role.id)) is None:
        session.add(UserRole(user_id=worker_id, role_id=admin_role.id))
    await session.flush()


async def run() -> None:
    if os.environ.get("ENVIRONMENT") != "development":
        raise RuntimeError("Local worker provisioning is permitted only in development.")
    migration_url = os.environ.get("MIGRATION_DATABASE_URL", "")
    if not migration_url:
        raise RuntimeError("MIGRATION_DATABASE_URL is required.")
    try:
        worker_id = UUID(os.environ["WORKER_USER_ID"])
    except (KeyError, ValueError) as error:
        raise RuntimeError("WORKER_USER_ID must be a valid UUID.") from error

    engine = create_async_engine(normalize_postgres_url(migration_url))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session, session.begin():
            await provision(session, worker_id=worker_id)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
