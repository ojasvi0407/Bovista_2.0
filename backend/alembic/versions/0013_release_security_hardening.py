"""Harden authentication, custody workflows, reference history, and outbox operations.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "auth_identities",
        sa.Column("mfa_failed_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "auth_identities",
        sa.Column("mfa_locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("outbox_events", sa.Column("last_error", sa.String(length=160), nullable=True))
    op.drop_index("ix_outbox_pending", table_name="outbox_events")
    op.create_index(
        "ix_outbox_due",
        "outbox_events",
        ["next_attempt_at", "created_at"],
        postgresql_where=sa.text(
            "published_at IS NULL AND dead_lettered_at IS NULL AND attempts < 30"
        ),
    )

    for table in ("diseases", "symptoms"):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_code_key")
        op.add_column(
            table,
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        )
        op.add_column(
            table,
            sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        )
    op.add_column(
        "symptoms", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.create_unique_constraint("uq_disease_code_revision", "diseases", ["code", "revision"])
    op.create_unique_constraint("uq_symptom_code_revision", "symptoms", ["code", "revision"])
    op.create_index(
        "uq_active_disease_code",
        "diseases",
        ["code"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_index(
        "uq_active_symptom_code",
        "symptoms",
        ["code"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.execute("DROP POLICY veterinary_cases_insert ON veterinary_cases")
    op.execute("DROP POLICY veterinary_cases_update ON veterinary_cases")
    case_roles = (
        "string_to_array(coalesce(current_setting('app.roles',true),''),',') "
        "&& ARRAY['ADMIN','VETERINARIAN']::text[]"
    )
    case_scope = (
        "EXISTS (SELECT 1 FROM disease_reports r "
        "WHERE r.id = veterinary_cases.disease_report_id)"
    )
    op.execute(
        "CREATE POLICY veterinary_cases_insert ON veterinary_cases FOR INSERT WITH CHECK ("
        f"({case_scope}) AND (({case_roles}) OR "
        "current_setting('app.internal_action',true)='risk.case.create'))"
    )
    op.execute(
        "CREATE POLICY veterinary_cases_update ON veterinary_cases FOR UPDATE "
        f"USING (({case_scope}) AND ({case_roles})) "
        f"WITH CHECK (({case_scope}) AND ({case_roles}))"
    )

    op.execute("DROP POLICY laboratory_samples_insert ON laboratory_samples")
    op.execute("DROP POLICY laboratory_samples_update ON laboratory_samples")
    lab_scope = (
        "EXISTS (SELECT 1 FROM disease_reports r "
        "WHERE r.id = laboratory_samples.disease_report_id)"
    )
    referral_roles = (
        "string_to_array(coalesce(current_setting('app.roles',true),''),',') "
        "&& ARRAY['ADMIN','VETERINARIAN','PARAVET']::text[]"
    )
    lab_roles = (
        "string_to_array(coalesce(current_setting('app.roles',true),''),',') "
        "&& ARRAY['ADMIN','VETERINARIAN','PARAVET','LAB_TECHNICIAN']::text[]"
    )
    op.execute(
        "CREATE POLICY laboratory_samples_insert ON laboratory_samples FOR INSERT "
        f"WITH CHECK (({lab_scope}) AND ({referral_roles}) AND status='REFERRED')"
    )
    op.execute(
        "CREATE POLICY laboratory_samples_update ON laboratory_samples FOR UPDATE "
        f"USING (({lab_scope}) AND ({lab_roles})) "
        f"WITH CHECK (({lab_scope}) AND ({lab_roles}))"
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_lab_transition() RETURNS trigger AS $$
        DECLARE roles text[] := string_to_array(
          coalesce(current_setting('app.roles', true), ''), ',');
        BEGIN
          IF NEW.disease_report_id IS DISTINCT FROM OLD.disease_report_id
             OR NEW.specimen_type IS DISTINCT FROM OLD.specimen_type
             OR NEW.lab_reference IS DISTINCT FROM OLD.lab_reference
             OR NEW.created_by_id IS DISTINCT FROM OLD.created_by_id
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
          THEN RAISE EXCEPTION 'laboratory custody fields are immutable'; END IF;
          IF NEW.status = OLD.status THEN
            RAISE EXCEPTION 'laboratory updates require a state transition';
          ELSIF OLD.status='REFERRED' AND NEW.status='COLLECTED' THEN
            IF NOT roles && ARRAY['ADMIN','VETERINARIAN','PARAVET']::text[]
            THEN RAISE EXCEPTION 'role cannot collect sample'; END IF;
          ELSIF OLD.status IN ('COLLECTED','RECEIVED','PROCESSING')
                AND NEW.status IN ('RECEIVED','PROCESSING','RESULTED') THEN
            IF NOT roles && ARRAY['ADMIN','LAB_TECHNICIAN']::text[]
            THEN RAISE EXCEPTION 'role cannot perform laboratory transition'; END IF;
            IF NOT ((OLD.status='COLLECTED' AND NEW.status='RECEIVED')
                 OR (OLD.status='RECEIVED' AND NEW.status='PROCESSING')
                 OR (OLD.status='PROCESSING' AND NEW.status='RESULTED'))
            THEN RAISE EXCEPTION 'invalid laboratory transition'; END IF;
          ELSIF OLD.status='RESULTED' AND NEW.status='REVIEWED' THEN
            IF NOT roles && ARRAY['ADMIN','VETERINARIAN']::text[]
            THEN RAISE EXCEPTION 'role cannot review result'; END IF;
          ELSE RAISE EXCEPTION 'invalid laboratory transition'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_lab_referral_case() RETURNS trigger AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM veterinary_cases c
            WHERE c.disease_report_id=NEW.disease_report_id AND c.status='REFERRED'
          ) THEN RAISE EXCEPTION 'sample requires a referred veterinary case'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER laboratory_referral_case BEFORE INSERT ON laboratory_samples "
        "FOR EACH ROW EXECUTE FUNCTION enforce_lab_referral_case()"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_lab_result_history() RETURNS trigger AS $$
        DECLARE roles text[] := string_to_array(
          coalesce(current_setting('app.roles', true), ''), ',');
        BEGIN
          IF NOT roles && ARRAY['ADMIN','LAB_TECHNICIAN']::text[]
          THEN RAISE EXCEPTION 'role cannot publish laboratory results'; END IF;
          IF NOT EXISTS (SELECT 1 FROM laboratory_samples s
            WHERE s.id=NEW.sample_id AND s.status='RESULTED')
          THEN RAISE EXCEPTION 'result requires a resulted sample'; END IF;
          IF NOT ('ADMIN'=ANY(roles)) AND NEW.published_by_id IS DISTINCT FROM
             nullif(current_setting('app.user_id', true), '')::uuid
          THEN RAISE EXCEPTION 'laboratory result actor mismatch'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER laboratory_result_history BEFORE INSERT ON laboratory_results "
        "FOR EACH ROW EXECUTE FUNCTION enforce_lab_result_history()"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_lab_transition_history() RETURNS trigger AS $$
        DECLARE roles text[] := string_to_array(
          coalesce(current_setting('app.roles', true), ''), ',');
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM laboratory_samples s
            WHERE s.id=NEW.sample_id AND s.status=NEW.to_state)
          THEN RAISE EXCEPTION 'transition does not match sample state'; END IF;
          IF NEW.to_state='COLLECTED' AND
             NOT roles && ARRAY['ADMIN','VETERINARIAN','PARAVET']::text[]
          THEN RAISE EXCEPTION 'role cannot record collection';
          ELSIF NEW.to_state IN ('RECEIVED','PROCESSING','RESULTED') AND
             NOT roles && ARRAY['ADMIN','LAB_TECHNICIAN']::text[]
          THEN RAISE EXCEPTION 'role cannot record laboratory work';
          ELSIF NEW.to_state='REVIEWED' AND
             NOT roles && ARRAY['ADMIN','VETERINARIAN']::text[]
          THEN RAISE EXCEPTION 'role cannot record result review'; END IF;
          IF NOT ('ADMIN'=ANY(roles)) AND NEW.actor_id IS DISTINCT FROM
             nullif(current_setting('app.user_id', true), '')::uuid
          THEN RAISE EXCEPTION 'laboratory transition actor mismatch'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER laboratory_transition_history BEFORE INSERT ON laboratory_transitions "
        "FOR EACH ROW EXECUTE FUNCTION enforce_lab_transition_history()"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_case_transition_history() RETURNS trigger AS $$
        DECLARE roles text[] := string_to_array(
          coalesce(current_setting('app.roles', true), ''), ',');
        BEGIN
          IF NOT roles && ARRAY['ADMIN','VETERINARIAN']::text[]
          THEN RAISE EXCEPTION 'role cannot record case transition'; END IF;
          IF NOT EXISTS (SELECT 1 FROM veterinary_cases c
            WHERE c.id=NEW.case_id AND c.status=NEW.to_state)
          THEN RAISE EXCEPTION 'transition does not match case state'; END IF;
          IF NOT ('ADMIN'=ANY(roles)) AND NEW.actor_id IS DISTINCT FROM
             nullif(current_setting('app.user_id', true), '')::uuid
          THEN RAISE EXCEPTION 'case transition actor mismatch'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    op.execute(
        "CREATE TRIGGER case_transition_history BEFORE INSERT ON case_transitions "
        "FOR EACH ROW EXECUTE FUNCTION enforce_case_transition_history()"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_reference_version_history() RETURNS trigger AS $$
        BEGIN
          IF TG_OP='DELETE' THEN
            RAISE EXCEPTION 'published reference version is immutable';
          END IF;
          IF NEW.code IS DISTINCT FROM OLD.code
             OR NEW.name IS DISTINCT FROM OLD.name
             OR NEW.revision IS DISTINCT FROM OLD.revision
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR (TG_TABLE_NAME='symptoms' AND NEW.severity IS DISTINCT FROM OLD.severity)
          THEN RAISE EXCEPTION 'published reference version is immutable'; END IF;
          IF OLD.active = false OR NEW.active = true OR NEW.retired_at IS NULL THEN
            RAISE EXCEPTION 'reference versions may only be retired once'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    for table in ("diseases", "symptoms"):
        op.execute(
            f"CREATE TRIGGER {table}_version_history BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION enforce_reference_version_history()"
        )


def downgrade():
    op.execute("DROP TRIGGER case_transition_history ON case_transitions")
    op.execute("DROP FUNCTION enforce_case_transition_history()")
    op.execute("DROP TRIGGER laboratory_transition_history ON laboratory_transitions")
    op.execute("DROP FUNCTION enforce_lab_transition_history()")
    op.execute("DROP TRIGGER laboratory_result_history ON laboratory_results")
    op.execute("DROP FUNCTION enforce_lab_result_history()")
    for table in ("diseases", "symptoms"):
        op.execute(f"DROP TRIGGER {table}_version_history ON {table}")
    op.execute("DROP FUNCTION enforce_reference_version_history()")
    op.execute("DROP TRIGGER laboratory_referral_case ON laboratory_samples")
    op.execute("DROP FUNCTION enforce_lab_referral_case()")
    op.drop_index("uq_active_symptom_code", table_name="symptoms")
    op.drop_index("uq_active_disease_code", table_name="diseases")
    op.drop_constraint("uq_symptom_code_revision", "symptoms")
    op.drop_constraint("uq_disease_code_revision", "diseases")
    op.drop_column("symptoms", "active")
    for table in ("symptoms", "diseases"):
        op.drop_column(table, "retired_at")
        op.drop_column(table, "revision")
        op.create_unique_constraint(f"{table}_code_key", table, ["code"])
    op.drop_index("ix_outbox_due", table_name="outbox_events")
    op.create_index("ix_outbox_pending", "outbox_events", ["published_at", "created_at"])
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "dead_lettered_at")
    op.drop_column("auth_identities", "mfa_locked_until")
    op.drop_column("auth_identities", "mfa_failed_attempts")
