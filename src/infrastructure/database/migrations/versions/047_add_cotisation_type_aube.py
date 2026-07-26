"""047 add AUBE to cotisationtype enum

La cotisation annuelle pour l'entretien/confection des aubes (Art. 21 du
reglement interieur, renouvelable chaque annee a partir du mois d'aout) est
distincte de la cotisation ordinaire et des cotisations evenementielles.

Revision ID: 047
Revises: 046
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE cotisationtype ADD VALUE IF NOT EXISTS 'AUBE'"))


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'enum sans reconstruire
    # le type. Downgrade = no-op (comme 033).
    pass
