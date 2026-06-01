"""Ajout du champ terms_accepted_at sur la table users (CGU)

Revision ID: 036
Revises: 035
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "terms_accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Date d'acceptation des CGU (Loi 2024/017 Art. 9 — traçabilité du consentement)",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_at")
