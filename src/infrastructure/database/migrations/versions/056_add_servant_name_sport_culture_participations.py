"""056 add servant_name to sport_culture_participations

`EventParticipation.servant_name` (src/core/entities/sport_culture.py) est
un champ enrichi renseigné par le repository au moment de l'inscription —
même pattern déjà en place pour `training_participations.servant_name`
(migration 019) — mais la colonne correspondante n'avait jamais été créée
en base. Toute requête sélectionnant le modèle complet (ex. GET
/sport-culture/stats) échouait avec UndefinedColumnError.

Revision ID: 056
Revises: 055
Create Date: 2026-07-20
"""
import sqlalchemy as sa

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sport_culture_participations",
        sa.Column("servant_name", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sport_culture_participations", "servant_name")
