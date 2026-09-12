"""deduplicate active potential outbreaks

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_active_potential_outbreak",
        "outbreaks",
        ["location_id", "disease_code", "config_version"],
        unique=True,
        postgresql_where=sa.text("state = 'POTENTIAL'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_potential_outbreak",
        table_name="outbreaks",
        postgresql_where=sa.text("state = 'POTENTIAL'"),
    )
