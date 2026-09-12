"""add Phase 4 alert and dashboard persistence

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enable_rls(table: str, predicate: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({predicate})")
    op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({predicate})")
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
        f"USING ({predicate}) WITH CHECK ({predicate})"
    )


def upgrade() -> None:
    op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True)))
    op.add_column("alerts", sa.Column("acknowledged_by_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_alerts_acknowledged_by_id_users",
        "alerts",
        "users",
        ["acknowledged_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_alerts_recipient_status_created",
        "alerts",
        ["recipient_id", "status", "created_at"],
    )
    op.create_table(
        "vaccinations",
        sa.Column("animal_id", sa.Uuid(), nullable=False),
        sa.Column("vaccine_name", sa.String(160), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("administered_on", sa.Date(), nullable=False),
        sa.Column("next_due_on", sa.Date()),
        sa.Column("administered_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["administered_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "animal_id",
            "vaccine_name",
            "batch_number",
            "administered_on",
            name="uq_vaccination_dose",
        ),
    )
    op.create_index("ix_vaccinations_animal_id", "vaccinations", ["animal_id"])
    op.create_index("ix_vaccinations_next_due", "vaccinations", ["next_due_on", "animal_id"])
    op.create_table(
        "laboratory_samples",
        sa.Column("disease_report_id", sa.Uuid(), nullable=False),
        sa.Column("specimen_type", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("lab_reference", sa.String(120)),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("resulted_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('REFERRED', 'COLLECTED', 'RECEIVED', 'PROCESSING', "
            "'RESULTED', 'REVIEWED')",
            name="ck_laboratory_samples_status",
        ),
        sa.ForeignKeyConstraint(["disease_report_id"], ["disease_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lab_reference"),
    )
    op.create_index(
        "ix_laboratory_samples_disease_report_id",
        "laboratory_samples",
        ["disease_report_id"],
    )
    op.create_index(
        "ix_laboratory_samples_status_created",
        "laboratory_samples",
        ["status", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_vaccination_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'vaccination records are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER vaccinations_immutable BEFORE UPDATE OR DELETE ON vaccinations "
        "FOR EACH ROW EXECUTE FUNCTION prevent_vaccination_mutation()"
    )
    _enable_rls(
        "vaccinations",
        "EXISTS (SELECT 1 FROM animals parent WHERE parent.id = vaccinations.animal_id)",
    )
    _enable_rls(
        "laboratory_samples",
        "EXISTS (SELECT 1 FROM disease_reports parent "
        "WHERE parent.id = laboratory_samples.disease_report_id)",
    )


def downgrade() -> None:
    for table in ("laboratory_samples", "vaccinations"):
        for operation in ("update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{operation} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS vaccinations_immutable ON vaccinations")
    op.execute("DROP FUNCTION IF EXISTS prevent_vaccination_mutation()")
    op.drop_table("laboratory_samples")
    op.drop_table("vaccinations")
    op.drop_index("ix_alerts_recipient_status_created", table_name="alerts")
    op.drop_constraint("fk_alerts_acknowledged_by_id_users", "alerts", type_="foreignkey")
    op.drop_column("alerts", "acknowledged_by_id")
    op.drop_column("alerts", "acknowledged_at")
