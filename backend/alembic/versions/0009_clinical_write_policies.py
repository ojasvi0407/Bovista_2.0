"""Restrict clinical writes and enforce case transitions.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

POLICIES = {
    "vaccinations": (
        "EXISTS (SELECT 1 FROM animals a WHERE a.id = vaccinations.animal_id)",
        "'ADMIN','VETERINARIAN','PARAVET'",
    ),
    "treatments": (
        "EXISTS (SELECT 1 FROM animals a WHERE a.id = treatments.animal_id)",
        "'ADMIN','VETERINARIAN'",
    ),
    "clinical_reversals": (
        "EXISTS (SELECT 1 FROM vaccinations v WHERE v.id = clinical_reversals.vaccination_id) "
        "OR EXISTS (SELECT 1 FROM treatments t WHERE t.id = clinical_reversals.treatment_id)",
        "'ADMIN','VETERINARIAN'",
    ),
    "laboratory_results": (
        "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_results.sample_id)",
        "'ADMIN','LAB_TECHNICIAN'",
    ),
    "laboratory_samples": (
        "EXISTS (SELECT 1 FROM disease_reports r WHERE r.id = laboratory_samples.disease_report_id)",
        "'ADMIN','VETERINARIAN','PARAVET','LAB_TECHNICIAN'",
    ),
    "laboratory_transitions": (
        "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_transitions.sample_id)",
        "'ADMIN','VETERINARIAN','PARAVET','LAB_TECHNICIAN'",
    ),
    "case_transitions": (
        "EXISTS (SELECT 1 FROM veterinary_cases c WHERE c.id = case_transitions.case_id)",
        "'ADMIN','VETERINARIAN'",
    ),
}


def policies(restrict):
    for table, (predicate, roles) in POLICIES.items():
        write = f"({predicate})"
        if restrict:
            write += (
                " AND string_to_array(coalesce(current_setting('app.roles',true),''),',')"
                f" && ARRAY[{roles}]::text[]"
            )
        op.execute(f"DROP POLICY {table}_insert ON {table}")
        op.execute(f"DROP POLICY {table}_update ON {table}")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({write})")
        op.execute(
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING ({write}) WITH CHECK ({write})"
        )


def upgrade():
    policies(True)
    op.execute("""
        CREATE FUNCTION enforce_case_transition() RETURNS trigger AS $$
        BEGIN
          IF NEW.status <> OLD.status AND NOT (
            (OLD.status='OPEN' AND NEW.status='IN_REVIEW') OR
            (OLD.status='IN_REVIEW' AND NEW.status IN ('REFERRED','CLOSED')) OR
            (OLD.status='REFERRED' AND NEW.status='IN_REVIEW')
          ) THEN RAISE EXCEPTION 'invalid case transition'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER veterinary_case_status_transition BEFORE UPDATE ON veterinary_cases FOR EACH ROW EXECUTE FUNCTION enforce_case_transition()"
    )


def downgrade():
    op.execute("DROP TRIGGER veterinary_case_status_transition ON veterinary_cases")
    op.execute("DROP FUNCTION enforce_case_transition()")
    policies(False)
