"""enforce submitted snapshot immutability

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION prevent_frozen_report_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status IN ('SUBMITTED', 'AMENDED') THEN
            RAISE EXCEPTION 'submitted disease reports are immutable';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER disease_reports_frozen
        BEFORE UPDATE OR DELETE ON disease_reports
        FOR EACH ROW EXECUTE FUNCTION prevent_frozen_report_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_frozen_report_child_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_report_id uuid;
        BEGIN
          target_report_id := CASE WHEN TG_OP = 'DELETE'
            THEN OLD.disease_report_id ELSE NEW.disease_report_id END;
          IF EXISTS (
            SELECT 1 FROM disease_reports
            WHERE id = target_report_id AND status IN ('SUBMITTED', 'AMENDED')
          ) THEN
            RAISE EXCEPTION 'submitted disease report snapshots are immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
        """
    )
    for table in (
        "disease_report_symptoms",
        "report_context_snapshots",
        "attachments",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_frozen BEFORE INSERT OR UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_frozen_report_child_mutation()"
        )


def downgrade() -> None:
    for table in (
        "attachments",
        "report_context_snapshots",
        "disease_report_symptoms",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_frozen ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_frozen_report_child_mutation()")
    op.execute("DROP TRIGGER IF EXISTS disease_reports_frozen ON disease_reports")
    op.execute("DROP FUNCTION IF EXISTS prevent_frozen_report_update()")
