"""046 add category to sub_groups + backfill from name

Le reglement interieur (Art. 26, 33-34) definit des sous-groupes precis
(Aspirants, Confirmes, Aines, Chorale) que le code reconnaissait jusqu'ici
par correspondance de nom exact et fragile. Cette migration ajoute une
categorie structuree et associe au mieux les groupes existants portant les
noms historiques (avec ou sans accents).

Revision ID: 046
Revises: 045
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sub_groups",
        sa.Column("category", sa.String(length=32), nullable=False, server_default="AUTRE"),
    )
    op.create_index("ix_sub_groups_category", "sub_groups", ["category"])

    # Best-effort : associer les groupes existants nommes historiquement
    # (avec ou sans accents) a leur categorie structuree.
    op.execute("UPDATE sub_groups SET category = 'ASPIRANTS' WHERE UPPER(name) = 'ASPIRANTS'")
    op.execute(
        "UPDATE sub_groups SET category = 'CONFIRMES' WHERE UPPER(name) IN ('CONFIRMÉS', 'CONFIRMES')"
    )
    op.execute(
        "UPDATE sub_groups SET category = 'AINES' WHERE UPPER(name) IN ('AÎNÉS', 'AINES', 'AINÉS', 'AINES')"
    )
    op.execute("UPDATE sub_groups SET category = 'CHORALE' WHERE UPPER(name) = 'CHORALE'")


def downgrade() -> None:
    op.drop_index("ix_sub_groups_category", table_name="sub_groups")
    op.drop_column("sub_groups", "category")
