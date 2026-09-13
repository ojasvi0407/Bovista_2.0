"""Protect audit rows and published rule content from mutation.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TRIGGER audit_logs_immutable BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION prevent_clinical_history_mutation()"
    )
    op.execute("""
        CREATE FUNCTION prevent_published_rule_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'published rule history cannot be deleted';
          END IF;
          IF (to_jsonb(NEW) - 'active' - 'updated_at') IS DISTINCT FROM
             (to_jsonb(OLD) - 'active' - 'updated_at') THEN
            RAISE EXCEPTION 'publish a new rule version to change content';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    for table in ("triage_rule_packs", "risk_rule_packs"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_published_rule_mutation()"
        )


def downgrade():
    for table in ("triage_rule_packs", "risk_rule_packs"):
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    op.execute("DROP FUNCTION prevent_published_rule_mutation()")
    op.execute("DROP TRIGGER audit_logs_immutable ON audit_logs")
