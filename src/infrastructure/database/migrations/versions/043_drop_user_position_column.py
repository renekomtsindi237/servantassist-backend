"""043 drop users.position (superseded by nominations table)

Nomination/PosteResponsable devient l'unique source de verite pour les
postes de responsable. Le champ legacy users.position (ServantPosition)
a ete migre vers la table nominations par la migration 042.

Revision ID: 043
Revises: 042
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "position")


def downgrade() -> None:
    # Colonne VARCHAR(64) restauree vide — les donnees legacy ne sont pas
    # reconstructibles depuis nominations (mapping non bijectif : un poste
    # PosteResponsable comme SECRETAIRE_GENERAL_ADJOINT n'a pas d'equivalent
    # unique dans l'ancien ServantPosition). Downgrade = perte de donnees
    # assumee, comme deja documente dans la migration 038.
    op.add_column("users", sa.Column("position", sa.String(length=64), nullable=True))
