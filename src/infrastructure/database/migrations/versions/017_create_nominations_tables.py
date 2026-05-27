"""create nominations and poste_actions tables

Revision ID: 017
Revises: 016
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_POSTE_VALUES = [
    "CONSEILLER",
    "DELEGUE",
    "VICE_DELEGUE",
    "SECRETAIRE_GENERAL",
    "SECRETAIRE_GENERAL_ADJOINT",
    "SECRETAIRE",
    "SECRETAIRE_ADJOINT",
    "CENSEUR",
    "CENSEUR_ADJOINT",
    "ECONOME",
    "COMMISSAIRE_AUX_COMPTES",
    "CHARGE_LITURGIE",
    "CHARGE_LITURGIE_ADJOINT",
    "CEREMONIAIRE",
    "CHARGE_CLASSEMENT_DIMANCHE",
    "CHARGE_CLASSEMENT_SEMAINE",
    "INTENDANT",
    "INTENDANT_ADJOINT",
    "CHARGE_SPORT_CULTURE",
    "CHARGE_SPORT_CULTURE_ADJOINT",
]

_ACTION_CATEGORY_VALUES = [
    "DECISION",
    "RAPPORT",
    "COMMUNICATION",
    "DISCIPLINE",
    "SANCTION",
    "CLASSEMENT",
    "FORMATION",
    "RECOLLECTION",
    "REPETITION",
    "COLLECTE",
    "DEPENSE",
    "BILAN_FINANCIER",
    "MATERIEL",
    "LAVAGE",
    "ACTIVITE_SPORTIVE",
    "ACTIVITE_CULTURELLE",
    "AUTRE",
]


def upgrade() -> None:
    op.create_table(
        "nominations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "poste",
            sa.Enum(*_POSTE_VALUES, name="posteresponsable"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "REVOQUEE", name="nominationstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("nominated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "nominated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nominated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nominations_user_id"), "nominations", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_nominations_poste"), "nominations", ["poste"], unique=False
    )
    op.create_index(
        op.f("ix_nominations_status"), "nominations", ["status"], unique=False
    )

    op.create_table(
        "poste_actions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "poste",
            sa.Enum(*_POSTE_VALUES, name="posteresponsable", create_constraint=False),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(*_ACTION_CATEGORY_VALUES, name="actioncategory"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.String(length=5000), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("action_date", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "BROUILLON",
                "PUBLIE",
                "EN_COURS",
                "TERMINE",
                "ANNULE",
                name="actionstatus",
            ),
            nullable=False,
            server_default="BROUILLON",
        ),
        sa.Column("extra_data", sa.String(length=10000), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["target_event_id"], ["events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_poste_actions_poste"), "poste_actions", ["poste"], unique=False
    )
    op.create_index(
        op.f("ix_poste_actions_category"), "poste_actions", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_poste_actions_status"), "poste_actions", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_poste_actions_status"), table_name="poste_actions")
    op.drop_index(op.f("ix_poste_actions_category"), table_name="poste_actions")
    op.drop_index(op.f("ix_poste_actions_poste"), table_name="poste_actions")
    op.drop_table("poste_actions")

    op.drop_index(op.f("ix_nominations_status"), table_name="nominations")
    op.drop_index(op.f("ix_nominations_poste"), table_name="nominations")
    op.drop_index(op.f("ix_nominations_user_id"), table_name="nominations")
    op.drop_table("nominations")

    sa.Enum(name="actionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="actioncategory").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="nominationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="posteresponsable").drop(op.get_bind(), checkfirst=True)
