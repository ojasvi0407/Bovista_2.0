"""Construct an async PostgreSQL URL from deployment-safe component variables."""

import os
from collections.abc import MutableMapping
from urllib.parse import quote


def normalize_postgres_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


def ensure_database_url(environment: MutableMapping[str, str] | None = None) -> str:
    target = environment if environment is not None else os.environ
    existing = target.get("DATABASE_URL")
    if existing:
        normalized = normalize_postgres_url(existing)
        target["DATABASE_URL"] = normalized
        return normalized
    required = (
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    )
    missing = [key for key in required if not target.get(key)]
    if missing:
        raise RuntimeError(f"Missing database configuration: {', '.join(missing)}")
    username = quote(target["DATABASE_USER"], safe="")
    password = quote(target["DATABASE_PASSWORD"], safe="")
    host = target["DATABASE_HOST"]
    port = target["DATABASE_PORT"]
    database = quote(target["DATABASE_NAME"], safe="")
    result = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
    target["DATABASE_URL"] = result
    return result
