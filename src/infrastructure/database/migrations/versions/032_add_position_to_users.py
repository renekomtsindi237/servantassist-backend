"""032 add position to users

Revision ID: 032
Revises: 031
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None

POSITIONS = [
    "DELEGUE", "VICE_DELEGUE", "CENSEUR", "CENSEUR_ADJOINT",
    "SECRETAIRE_GENERAL", "SECRETAIRE_GENERAL_ADJOINT",
    "ECONOME", "INTENDANT", "CHARGE_LITURGIE",
    "CHARGE_SPORTS_CULTURE", "CHARGE_CLASSEMENT",
    "CONSEILLER", "SERVANT_AUTEL",
]


def upgrade() -> None:
    servant_position_enum = sa.Enum(*POSITIONS, name="servantposition")
    servant_position_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column("position", servant_position_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "position")
    sa.Enum(name="servantposition").drop(op.get_bind(), checkfirst=True)
