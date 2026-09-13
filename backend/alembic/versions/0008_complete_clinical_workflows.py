"""Complete clinical records and laboratory custody history.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

PREDICATES = {
    "treatments": "EXISTS (SELECT 1 FROM animals a WHERE a.id = treatments.animal_id)",
    "clinical_reversals": (
        "EXISTS (SELECT 1 FROM vaccinations v WHERE v.id = clinical_reversals.vaccination_id) "
        "OR EXISTS (SELECT 1 FROM treatments t WHERE t.id = clinical_reversals.treatment_id)"
    ),
    "laboratory_results": "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_results.sample_id)",
    "laboratory_transitions": "EXISTS (SELECT 1 FROM laboratory_samples s WHERE s.id = laboratory_transitions.sample_id)",
    "case_transitions": "EXISTS (SELECT 1 FROM veterinary_cases c WHERE c.id = case_transitions.case_id)",
}


def identifier():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def reference(name, target, *, nullable=False, unique=False):
    return sa.Column(
        name,
        sa.Uuid(),
        sa.ForeignKey(target, ondelete="RESTRICT"),
        nullable=nullable,
        unique=unique,
    )


def upgrade():
    op.add_column("herds", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "treatments",
        identifier(),
        reference("animal_id", "animals.id"),
        reference("case_id", "veterinary_cases.id"),
        sa.Column("medicine_name", sa.String(160), nullable=False),
        sa.Column("dosage", sa.Numeric(12, 4), nullable=False),
        sa.Column("dosage_unit", sa.String(40), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("administered_on", sa.Date(), nullable=False),
        reference("recorded_by_id", "users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("dosage > 0 AND duration_days > 0", name="ck_treatment_positive"),
    )
    op.create_index("ix_treatments_animal_id", "treatments", ["animal_id"])
    op.create_index("ix_treatments_case_id", "treatments", ["case_id"])
    op.create_table(
        "clinical_reversals",
        identifier(),
        reference("vaccination_id", "vaccinations.id", nullable=True, unique=True),
        reference("treatment_id", "treatments.id", nullable=True, unique=True),
        sa.Column("reason", sa.String(1000), nullable=False),
        reference("actor_id", "users.id"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(vaccination_id IS NULL) <> (treatment_id IS NULL)", name="ck_reversal_target"
        ),
    )
    op.create_table(
        "laboratory_results",
        identifier(),
        reference("sample_id", "laboratory_samples.id", unique=True),
        sa.Column("disease_code", sa.String(60), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("findings", sa.String(4000), nullable=False),
        reference("published_by_id", "users.id"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('POSITIVE', 'NEGATIVE', 'INCONCLUSIVE')", name="ck_lab_outcome"
        ),
    )
    for table, parent, target in (
        ("laboratory_transitions", "sample_id", "laboratory_samples.id"),
        ("case_transitions", "case_id", "veterinary_cases.id"),
    ):
        op.create_table(
            table,
            identifier(),
            reference(parent, target),
            reference("actor_id", "users.id"),
            sa.Column("from_state", sa.String(24), nullable=False),
            sa.Column("to_state", sa.String(24), nullable=False),
            sa.Column("reason", sa.String(1000), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(f"ix_{table}_{parent}", table, [parent])
    op.execute("""
        CREATE FUNCTION prevent_clinical_history_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'clinical history is immutable'; END;
        $$ LANGUAGE plpgsql
    """)
    for table, predicate in PREDICATES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({predicate})")
        op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({predicate})")
        op.execute(
            f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING ({predicate}) WITH CHECK ({predicate})"
        )
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_clinical_history_mutation()"
        )
    # The report remains inaccessible through report APIs to lab technicians.
    # Its SELECT policy allows scoped lab joins without elevating a lab request.
    op.execute("""
        CREATE POLICY laboratory_report_read ON disease_reports FOR SELECT USING (
            'LAB_TECHNICIAN' = ANY(string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
            AND coalesce(current_setting('app.location_path', true), '') <> ''
            AND location_path LIKE current_setting('app.location_path', true) || '%'
        )
    """)
    op.execute("""
        CREATE FUNCTION enforce_lab_transition() RETURNS trigger AS $$
        BEGIN
          IF NEW.status <> OLD.status AND NOT (
            (OLD.status='REFERRED' AND NEW.status='COLLECTED') OR
            (OLD.status='COLLECTED' AND NEW.status='RECEIVED') OR
            (OLD.status='RECEIVED' AND NEW.status='PROCESSING') OR
            (OLD.status='PROCESSING' AND NEW.status='RESULTED') OR
            (OLD.status='RESULTED' AND NEW.status='REVIEWED')
          ) THEN RAISE EXCEPTION 'invalid laboratory transition'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER laboratory_status_transition BEFORE UPDATE ON laboratory_samples FOR EACH ROW EXECUTE FUNCTION enforce_lab_transition()"
    )


def downgrade():
    op.execute("DROP TRIGGER laboratory_status_transition ON laboratory_samples")
    op.execute("DROP FUNCTION enforce_lab_transition()")
    op.execute("DROP POLICY laboratory_report_read ON disease_reports")
    for table in reversed(PREDICATES):
        op.drop_table(table)
    op.execute("DROP FUNCTION prevent_clinical_history_mutation()")
    op.drop_column("herds", "deleted_at")
