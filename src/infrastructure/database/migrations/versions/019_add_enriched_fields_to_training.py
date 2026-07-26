"""add enriched fields to training tables

Revision ID: 024
Revises: 023
Create Date: 2026-05-22

These fields are computed in-memory by enrich_session/enrich_participation
but must exist as DB columns because SQLModel maps every field to a column.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "training_sessions",
        sa.Column("trainer_name", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column(
            "current_participants",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "training_participations",
        sa.Column("servant_name", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "training_materials",
        sa.Column("uploaded_by_name", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("training_materials", "uploaded_by_name")
    op.drop_column("training_participations", "servant_name")
    op.drop_column("training_sessions", "current_participants")
    op.drop_column("training_sessions", "trainer_name")
