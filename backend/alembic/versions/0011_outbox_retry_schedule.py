"""Persist retry scheduling for the outbox dispatcher.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("outbox_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("outbox_events", "next_attempt_at")
