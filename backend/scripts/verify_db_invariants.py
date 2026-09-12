import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        postgis = await connection.scalar(text("SELECT PostGIS_Version()"))
        forced_rls_tables = await connection.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_class
                WHERE relname = ANY(
                    ARRAY[
                        'farms', 'herds', 'animals', 'disease_reports',
                        'disease_report_symptoms', 'report_context_snapshots',
                        'attachments', 'triage_results', 'triage_findings',
                        'risk_scores', 'risk_factor_contributions',
                        'veterinary_cases', 'alerts',
                        'outbreak_report_memberships', 'vaccinations',
                        'laboratory_samples'
                    ]
                )
                AND relforcerowsecurity
                """
            )
        )
        frozen_triggers = await connection.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_trigger
                WHERE NOT tgisinternal AND tgname LIKE '%_frozen'
                """
            )
        )
        outbreak_dedup_indexes = await connection.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_indexes
                WHERE indexname = 'uq_active_potential_outbreak'
                """
            )
        )
        active_animal_indexes = await connection.scalar(
            text("SELECT count(*) FROM pg_indexes " "WHERE indexname = 'ix_animals_active_farm'")
        )
        mfa_challenge_table = await connection.scalar(
            text("SELECT to_regclass('mfa_challenges') IS NOT NULL")
        )
        phase4_tables = await connection.scalar(
            text(
                "SELECT to_regclass('vaccinations') IS NOT NULL "
                "AND to_regclass('laboratory_samples') IS NOT NULL"
            )
        )
        vaccination_immutable = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgname = 'vaccinations_immutable'"
            )
        )

    await engine.dispose()
    checks = {
        "postgis": bool(postgis),
        "forced_rls_tables": forced_rls_tables == 16,
        "frozen_triggers": frozen_triggers == 4,
        "outbreak_dedup_index": outbreak_dedup_indexes == 1,
        "active_animal_index": active_animal_indexes == 1,
        "mfa_challenge_table": bool(mfa_challenge_table),
        "phase4_tables": bool(phase4_tables),
        "vaccination_immutable": vaccination_immutable == 1,
    }
    for name, passed in checks.items():
        print(f"{name}={'ok' if passed else 'failed'}")
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise RuntimeError(f"Database invariant checks failed: {', '.join(failures)}")


if __name__ == "__main__":
    asyncio.run(main())
