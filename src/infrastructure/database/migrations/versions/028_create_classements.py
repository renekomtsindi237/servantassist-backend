"""create classements table

Revision ID: 028
Revises: 027
Create Date: 2026-05-24
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="BROUILLON"),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("heure", sa.String(10), nullable=False),
        sa.Column("lieu", sa.String(200), nullable=False),
        sa.Column("solennite", sa.String(200), nullable=True),
        sa.Column("couleur_liturgique", sa.String(20), nullable=True),
        sa.Column("semaine", sa.Integer(), nullable=True),
        sa.Column("annee", sa.Integer(), nullable=True),
        sa.Column("horaire", sa.String(10), nullable=True),
        sa.Column("type_extra", sa.String(30), nullable=True),
        sa.Column("participants", sa.Text(), nullable=True),
        sa.Column("postes", JSON, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_classements_type", "classements", ["type"])
    op.create_index("ix_classements_status", "classements", ["status"])
    op.create_index("ix_classements_created_at", "classements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_classements_created_at", "classements")
    op.drop_index("ix_classements_status", "classements")
    op.drop_index("ix_classements_type", "classements")
    op.drop_table("classements")
