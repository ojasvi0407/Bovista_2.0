"""force RLS across identifiable livestock records

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FARM_ACCESS = """
(
  'ADMIN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
  OR owner_id = nullif(current_setting('app.user_id', true), '')::uuid
  OR (
    ('VETERINARIAN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
     OR 'PARAVET' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ',')))
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

PREDICATES = {
    "farms": FARM_ACCESS,
    "herds": "EXISTS (SELECT 1 FROM farms p WHERE p.id = herds.farm_id)",
    "animals": "EXISTS (SELECT 1 FROM farms p WHERE p.id = animals.farm_id)",
    "disease_report_symptoms": (
        "EXISTS (SELECT 1 FROM disease_reports p "
        "WHERE p.id = disease_report_symptoms.disease_report_id)"
    ),
    "report_context_snapshots": (
        "EXISTS (SELECT 1 FROM disease_reports p "
        "WHERE p.id = report_context_snapshots.disease_report_id)"
    ),
    "attachments": (
        "EXISTS (SELECT 1 FROM disease_reports p " "WHERE p.id = attachments.disease_report_id)"
    ),
    "triage_results": (
        "EXISTS (SELECT 1 FROM disease_reports p " "WHERE p.id = triage_results.disease_report_id)"
    ),
    "risk_scores": (
        "EXISTS (SELECT 1 FROM disease_reports p " "WHERE p.id = risk_scores.disease_report_id)"
    ),
    "veterinary_cases": (
        "EXISTS (SELECT 1 FROM disease_reports p "
        "WHERE p.id = veterinary_cases.disease_report_id)"
    ),
    "alerts": ("EXISTS (SELECT 1 FROM disease_reports p " "WHERE p.id = alerts.disease_report_id)"),
    "outbreak_report_memberships": (
        "EXISTS (SELECT 1 FROM disease_reports p "
        "WHERE p.id = outbreak_report_memberships.disease_report_id)"
    ),
    "triage_findings": (
        "EXISTS (SELECT 1 FROM triage_results p " "WHERE p.id = triage_findings.triage_result_id)"
    ),
    "risk_factor_contributions": (
        "EXISTS (SELECT 1 FROM risk_scores p "
        "WHERE p.id = risk_factor_contributions.risk_score_id)"
    ),
}


def upgrade() -> None:
    for table, predicate in PREDICATES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({predicate})")
        op.execute(
            f"CREATE POLICY {table}_insert ON {table} " f"FOR INSERT WITH CHECK ({predicate})"
        )
        op.execute(
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade() -> None:
    for table in reversed(PREDICATES):
        for operation in ("update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{operation} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
