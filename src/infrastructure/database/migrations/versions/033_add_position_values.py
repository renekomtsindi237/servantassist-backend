"""033 add CEREMONIARE and COMMISSAIRE_AUX_COMPTES to servantposition enum

Revision ID: 033
Revises: 032
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE cannot run inside a standard transaction block
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "ALTER TYPE servantposition ADD VALUE IF NOT EXISTS 'CEREMONIARE'"
        ))
        op.execute(sa.text(
            "ALTER TYPE servantposition ADD VALUE IF NOT EXISTS 'COMMISSAIRE_AUX_COMPTES'"
        ))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is a no-op; remove values manually if needed.
    pass
