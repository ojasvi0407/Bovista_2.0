from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import CurrentPrincipal

REPORT_ACCESS_PREDICATE = """
(
    'ADMIN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
    OR reporter_id = nullif(current_setting('app.user_id', true), '')::uuid
    OR (
        (
            'VETERINARIAN' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
            OR 'LAB_TECHNICIAN' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
            OR 'PARAVET' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
        )
        AND location_path LIKE coalesce(current_setting('app.location_path', true), '') || '%'
        AND coalesce(current_setting('app.location_path', true), '') <> ''
    )
    OR (
        'DISTRICT_OFFICER' = ANY(
            string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
        )
        AND EXISTS (
            SELECT 1 FROM case_review_grants review_grant
            WHERE review_grant.disease_report_id = disease_reports.id
              AND review_grant.grantee_id = nullif(current_setting('app.user_id', true), '')::uuid
              AND review_grant.revoked_at IS NULL
              AND review_grant.expires_at > now()
        )
    )
)
"""

REPORT_WRITE_PREDICATE = """
(
    'ADMIN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
    OR reporter_id = nullif(current_setting('app.user_id', true), '')::uuid
    OR (
        (
            'VETERINARIAN' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
            OR 'PARAVET' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
        )
        AND location_path LIKE coalesce(current_setting('app.location_path', true), '') || '%'
        AND coalesce(current_setting('app.location_path', true), '') <> ''
    )
)
"""

REPORT_RLS_DDL = (
    "ALTER TABLE disease_reports ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE disease_reports FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS disease_reports_select ON disease_reports",
    (
        "CREATE POLICY disease_reports_select ON disease_reports "
        f"FOR SELECT USING {REPORT_ACCESS_PREDICATE}"
    ),
    "DROP POLICY IF EXISTS disease_reports_insert ON disease_reports",
    (
        "CREATE POLICY disease_reports_insert ON disease_reports "
        f"FOR INSERT WITH CHECK {REPORT_WRITE_PREDICATE}"
    ),
    "DROP POLICY IF EXISTS disease_reports_update ON disease_reports",
    (
        "CREATE POLICY disease_reports_update ON disease_reports "
        f"FOR UPDATE USING {REPORT_WRITE_PREDICATE} "
        f"WITH CHECK {REPORT_WRITE_PREDICATE}"
    ),
)

FARM_ACCESS_PREDICATE = """
(
    'ADMIN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
    OR owner_id = nullif(current_setting('app.user_id', true), '')::uuid
    OR (
        (
            'VETERINARIAN' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
            OR 'PARAVET' = ANY(
                string_to_array(coalesce(current_setting('app.roles', true), ''), ',')
            )
        )
        AND EXISTS (
            SELECT 1 FROM locations scoped_location
            WHERE scoped_location.id = farms.location_id
              AND scoped_location.hierarchy_path LIKE
                  coalesce(current_setting('app.location_path', true), '') || '%'
              AND coalesce(current_setting('app.location_path', true), '') <> ''
        )
    )
)
"""


def _policy_ddl(table: str, predicate: str) -> tuple[str, ...]:
    writers = {
        "vaccinations": ("ADMIN", "VETERINARIAN", "PARAVET"),
        "treatments": ("ADMIN", "VETERINARIAN"),
        "clinical_reversals": ("ADMIN", "VETERINARIAN"),
        "laboratory_results": ("ADMIN", "LAB_TECHNICIAN"),
        "laboratory_samples": ("ADMIN", "VETERINARIAN", "PARAVET", "LAB_TECHNICIAN"),
        "laboratory_transitions": ("ADMIN", "VETERINARIAN", "PARAVET", "LAB_TECHNICIAN"),
        "case_transitions": ("ADMIN", "VETERINARIAN"),
        "veterinary_cases": ("ADMIN", "VETERINARIAN"),
    }
    insert_predicate = predicate
    update_predicate = predicate
    if table in writers:
        literals = ", ".join("'" + role + "'" for role in writers[table])
        role_predicate = (
            f"({predicate}) AND "
            "string_to_array(coalesce(current_setting('app.roles', true), ''), ',') "
            f"&& ARRAY[{literals}]::text[]"
        )
        insert_predicate = role_predicate
        update_predicate = role_predicate
    if table == "laboratory_samples":
        insert_predicate = (
            f"({predicate}) AND status = 'REFERRED' AND "
            "string_to_array(coalesce(current_setting('app.roles', true), ''), ',') "
            "&& ARRAY['ADMIN','VETERINARIAN','PARAVET']::text[]"
        )
    if table == "veterinary_cases":
        insert_predicate = (
            f"({predicate}) AND (({insert_predicate}) OR "
            "current_setting('app.internal_action', true) = 'risk.case.create')"
        )
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {table}_select ON {table}",
        f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({predicate})",
        f"DROP POLICY IF EXISTS {table}_insert ON {table}",
        f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({insert_predicate})",
        f"DROP POLICY IF EXISTS {table}_update ON {table}",
        (
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
            f"USING ({update_predicate}) WITH CHECK ({update_predicate})"
        ),
    )


DOMAIN_RLS_PREDICATES = {
    "treatments": "EXISTS (SELECT 1 FROM animals a WHERE a.id = treatments.animal_id)",
    "clinical_reversals": (
        "EXISTS (SELECT 1 FROM vaccinations v WHERE v.id = clinical_reversals.vaccination_id) "
        "OR EXISTS (SELECT 1 FROM treatments t WHERE t.id = clinical_reversals.treatment_id)"
    ),
    "laboratory_results": (
        "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_results.sample_id)"
    ),
    "laboratory_transitions": (
        "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_transitions.sample_id)"
    ),
    "case_transitions": (
        "EXISTS (SELECT 1 FROM veterinary_cases c WHERE c.id = case_transitions.case_id)"
    ),
    "farms": FARM_ACCESS_PREDICATE,
    "herds": "EXISTS (SELECT 1 FROM farms parent WHERE parent.id = herds.farm_id)",
    "animals": "EXISTS (SELECT 1 FROM farms parent WHERE parent.id = animals.farm_id)",
    "vaccinations": (
        "EXISTS (SELECT 1 FROM animals parent WHERE parent.id = vaccinations.animal_id)"
    ),
    "disease_report_symptoms": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = disease_report_symptoms.disease_report_id)"
    ),
    "report_context_snapshots": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = report_context_snapshots.disease_report_id)"
    ),
    "attachments": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = attachments.disease_report_id)"
    ),
    "laboratory_samples": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = laboratory_samples.disease_report_id)"
    ),
    "triage_results": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = triage_results.disease_report_id)"
    ),
    "risk_scores": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = risk_scores.disease_report_id)"
    ),
    "veterinary_cases": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = veterinary_cases.disease_report_id)"
    ),
    "alerts": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = alerts.disease_report_id)"
    ),
    "outbreak_report_memberships": (
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = outbreak_report_memberships.disease_report_id)"
    ),
    "triage_findings": (
        "EXISTS (SELECT 1 FROM triage_results parent "
        "WHERE parent.id = triage_findings.triage_result_id)"
    ),
    "risk_factor_contributions": (
        "EXISTS (SELECT 1 FROM risk_scores parent "
        "WHERE parent.id = risk_factor_contributions.risk_score_id)"
    ),
}

DOMAIN_RLS_DDL = tuple(
    statement
    for table, predicate in DOMAIN_RLS_PREDICATES.items()
    for statement in _policy_ddl(table, predicate)
)
RLS_DDL = REPORT_RLS_DDL + DOMAIN_RLS_DDL


async def apply_rls(session: AsyncSession) -> None:
    for statement in RLS_DDL:
        await session.execute(text(statement))


async def remove_rls(session: AsyncSession) -> None:
    for table in ("disease_reports", *DOMAIN_RLS_PREDICATES):
        for operation in ("select", "insert", "update"):
            await session.execute(text(f"DROP POLICY IF EXISTS {table}_{operation} ON {table}"))
        await session.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))


async def set_rls_context(session: AsyncSession, principal: CurrentPrincipal) -> None:
    await session.execute(
        text("SELECT set_config('app.user_id', :value, true)"),
        {"value": str(principal.user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.roles', :value, true)"),
        {"value": ",".join(sorted(principal.roles))},
    )
    await session.execute(
        text("SELECT set_config('app.location_path', :value, true)"),
        {"value": principal.location_path or ""},
    )
