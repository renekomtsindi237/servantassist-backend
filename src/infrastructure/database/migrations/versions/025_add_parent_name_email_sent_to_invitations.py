"""add parent_name and email_sent to invitation_codes

Revision ID: 025
Revises: 024
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invitation_codes", sa.Column("parent_name", sa.String(), nullable=True)
    )
    op.add_column(
        "invitation_codes",
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("invitation_codes", "email_sent")
    op.drop_column("invitation_codes", "parent_name")
