"""add birth_date and baptism_date to users

Revision ID: 020
Revises: 019
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("baptism_date", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "baptism_date")
    op.drop_column("users", "birth_date")
