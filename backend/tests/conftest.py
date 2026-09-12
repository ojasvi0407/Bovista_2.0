import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import decisions, geography, identity, reports, surveillance, trust  # noqa: F401

TEST_DATABASE_URL = os.environ.get(
    "BOVISTA_TEST_DATABASE_URL",
    "postgresql+asyncpg://bovista_test:BovistaTest_2026%21ChangeMe@127.0.0.1:5432/bovista_test",
)

if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    raise RuntimeError("Refusing to run tests against a database not ending in '_test'.")


async def _drop_test_rls_policies(connection) -> None:
    policies = await connection.execute(
        text(
            "SELECT schemaname, tablename, policyname FROM pg_policies "
            "WHERE schemaname = current_schema()"
        )
    )
    for schema, table, policy in policies.all():
        await connection.execute(text(f'DROP POLICY IF EXISTS "{policy}" ON "{schema}"."{table}"'))


async def _drop_snapshot_functions(connection) -> None:
    await connection.execute(text("DROP FUNCTION IF EXISTS prevent_frozen_report_update()"))
    await connection.execute(text("DROP FUNCTION IF EXISTS prevent_frozen_report_child_mutation()"))


async def _drop_test_migration_state(connection) -> None:
    # The test database is rebuilt from ORM metadata for every test. Keeping an
    # Alembic revision marker after those tables are dropped makes the schema
    # appear migrated when it is actually empty.
    await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        if await connection.scalar(text("SELECT to_regclass('disease_reports') IS NOT NULL")):
            await _drop_test_rls_policies(connection)
        await connection.run_sync(Base.metadata.drop_all)
        await _drop_test_migration_state(connection)
        await _drop_snapshot_functions(connection)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session

    async with engine.begin() as connection:
        await _drop_test_rls_policies(connection)
        await connection.run_sync(Base.metadata.drop_all)
        await _drop_test_migration_state(connection)
        await _drop_snapshot_functions(connection)
    await engine.dispose()
