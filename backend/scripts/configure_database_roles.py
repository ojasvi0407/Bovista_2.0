"""Provision non-owning API and worker roles after owner-run migrations."""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.database_url import normalize_postgres_url

ROLES = ("pashumitra_runtime", "pashumitra_worker")


async def configure() -> None:
    migration_url = os.environ.get("MIGRATION_DATABASE_URL", "")
    passwords = {
        "pashumitra_runtime": os.environ.get("DATABASE_PASSWORD", ""),
        "pashumitra_worker": os.environ.get("WORKER_DATABASE_PASSWORD", ""),
    }
    if not migration_url:
        raise RuntimeError("MIGRATION_DATABASE_URL is required.")
    if any(len(value) < 32 for value in passwords.values()):
        raise RuntimeError("Runtime and worker database passwords must be at least 32 characters.")
    engine = create_async_engine(normalize_postgres_url(migration_url))
    try:
        async with engine.begin() as connection:
            for role in ROLES:
                create_role_sql = (
                    "DO $$ BEGIN IF NOT EXISTS "  # noqa: S608 - fixed role tuple
                    f"(SELECT 1 FROM pg_roles WHERE rolname='{role}') "
                    f"THEN CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS "
                    "NOCREATEDB NOCREATEROLE NOINHERIT; END IF; END $$"
                )
                await connection.execute(text(create_role_sql))
                quoted_password = await connection.scalar(
                    text("SELECT quote_literal(:password)"),
                    {"password": passwords[role]},
                )
                alter_role_sql = (
                    f"ALTER ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS "
                    f"NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {quoted_password}"
                )  # noqa: S608 - fixed role plus server-escaped password literal
                await connection.execute(text(alter_role_sql))
            database_grants = await connection.scalar(
                text(
                    "SELECT format('GRANT CONNECT ON DATABASE %I TO "
                    "pashumitra_runtime, pashumitra_worker', current_database())"
                )
            )
            await connection.execute(text(database_grants))
            await connection.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
            await connection.execute(
                text("GRANT USAGE ON SCHEMA public TO pashumitra_runtime, pashumitra_worker")
            )
            await connection.execute(
                text(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                    "TO pashumitra_runtime, pashumitra_worker"
                )
            )
            await connection.execute(
                text(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
                    "TO pashumitra_runtime, pashumitra_worker"
                )
            )
            await connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES "
                    "TO pashumitra_runtime, pashumitra_worker"
                )
            )
            await connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT USAGE, SELECT ON SEQUENCES TO pashumitra_runtime, pashumitra_worker"
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(configure())
