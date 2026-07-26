"""add session_type to attendance_sessions

Revision ID: 029
Revises: 028
Create Date: 2026-05-24
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendance_sessions",
        sa.Column(
            "session_type",
            sa.String(30),
            nullable=False,
            server_default="REUNION_HEBDOMADAIRE",
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance_sessions", "session_type")
