"""Persist MFA challenge attempt limits.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mfa_challenges",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.alter_column("mfa_challenges", "attempts", server_default=None)


def downgrade():
    op.drop_column("mfa_challenges", "attempts")
