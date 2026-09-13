import pytest
from sqlalchemy import inspect, text

from app.models import (  # noqa: F401
    clinical,
    decisions,
    geography,
    identity,
    laboratory,
    reports,
    surveillance,
)


@pytest.mark.asyncio
async def test_core_schema_contains_architecture_tables(session) -> None:
    connection = await session.connection()
    tables = await connection.run_sync(
        lambda sync_connection: set(inspect(sync_connection).get_table_names())
    )

    assert {
        "users",
        "roles",
        "staff_geographic_assignments",
        "locations",
        "farms",
        "disease_reports",
        "triage_rule_packs",
        "triage_results",
        "risk_rule_packs",
        "risk_scores",
        "veterinary_cases",
        "alerts",
        "vaccinations",
        "laboratory_samples",
        "outbreaks",
        "audit_logs",
        "idempotency_receipts",
        "outbox_events",
    }.issubset(tables)


@pytest.mark.asyncio
async def test_postgis_is_enabled(session) -> None:
    version = await session.scalar(text("SELECT PostGIS_Version()"))

    assert version.startswith("3.")
