"""041 add ACCOMPAGNATEUR to posteresponsable enum

Ajoute le poste d'Accompagnateur (Art. 4-5 du reglement interieur) au systeme
de nominations. Ce poste n'existait pas dans le systeme informatique.

Revision ID: 041
Revises: 040
Create Date: 2026-07-16
"""
import sqlalchemy as sa

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE ne peut pas s'executer dans une transaction standard.
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "ALTER TYPE posteresponsable ADD VALUE IF NOT EXISTS 'ACCOMPAGNATEUR'"
        ))


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'enum sans reconstruire
    # le type. Downgrade = no-op (comme 033).
    pass
