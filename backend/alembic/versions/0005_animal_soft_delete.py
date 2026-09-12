"""add animal soft-delete timestamp

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("animals", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_animals_active_farm",
        "animals",
        ["farm_id", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_animals_active_farm", table_name="animals")
    op.drop_column("animals", "deleted_at")
