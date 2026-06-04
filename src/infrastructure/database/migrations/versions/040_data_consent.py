"""Ajout du champ data_consent_at sur la table users

Enregistre le consentement explicite de l'utilisateur au traitement de ses données
personnelles, conformément à l'article 9 de la Loi n° 2024/017 du 22 décembre 2024
relative à la protection des données à caractère personnel au Cameroun.

Revision ID: 040
Revises: 039
Create Date: 2026-06-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "040"
down_revision: Union[str, None] = "039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("data_consent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "data_consent_at")
