import asyncio
import os

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        postgis = await connection.scalar(text("SELECT PostGIS_Version()"))
        forced_rls_tables = await connection.scalar(text("""
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
                        'laboratory_samples', 'treatments', 'clinical_reversals',
                        'laboratory_results', 'laboratory_transitions', 'case_transitions'
                    ]
                )
                AND relforcerowsecurity
                """))
        frozen_triggers = await connection.scalar(text("""
                SELECT count(*)
                FROM pg_trigger
                WHERE NOT tgisinternal AND tgname LIKE '%_frozen'
                """))
        outbreak_dedup_indexes = await connection.scalar(text("""
                SELECT count(*)
                FROM pg_indexes
                WHERE indexname = 'uq_active_potential_outbreak'
                """))
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
        history_triggers = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname = ANY(ARRAY["
                "'treatments_immutable','clinical_reversals_immutable','laboratory_results_immutable',"
                "'laboratory_transitions_immutable','case_transitions_immutable','audit_logs_immutable',"
                "'triage_rule_packs_immutable','risk_rule_packs_immutable',"
                "'diseases_version_history','symptoms_version_history'])"
            )
        )
        state_triggers = await connection.scalar(
            text(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname = ANY("
                "ARRAY['laboratory_status_transition','veterinary_case_status_transition'])"
            )
        )
        runtime_safe = await connection.scalar(
            text(
                "SELECT NOT rolsuper AND NOT rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )
        )
        runtime_owns_domain_tables = await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n "
                "ON n.oid=c.relnamespace WHERE n.nspname=current_schema() "
                "AND c.relkind IN ('r','p') AND c.relowner=(SELECT oid FROM pg_roles "
                "WHERE rolname=current_user))"
            )
        )

    await engine.dispose()
    checks = {
        "postgis": bool(postgis),
        "forced_rls_tables": forced_rls_tables == 21,
        "frozen_triggers": frozen_triggers == 4,
        "outbreak_dedup_index": outbreak_dedup_indexes == 1,
        "active_animal_index": active_animal_indexes == 1,
        "mfa_challenge_table": bool(mfa_challenge_table),
        "phase4_tables": bool(phase4_tables),
        "vaccination_immutable": vaccination_immutable == 1,
        "clinical_audit_rule_history": history_triggers == 13,
        "workflow_state_triggers": state_triggers == 2,
        "runtime_role_enforces_rls": bool(runtime_safe),
    }
    if os.environ.get("REQUIRE_NONOWNER_DATABASE_ROLE") == "1":
        checks["runtime_role_owns_no_domain_tables"] = not runtime_owns_domain_tables
    for name, passed in checks.items():
        print(f"{name}={'ok' if passed else 'failed'}")
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise RuntimeError(f"Database invariant checks failed: {', '.join(failures)}")


if __name__ == "__main__":
    asyncio.run(main())
