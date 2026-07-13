"""create discipline_cases table

Revision ID: 015
Revises: 014
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discipline_cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("accused_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "offense_category",
            sa.Enum(
                "ABSENCE_NON_JUSTIFIEE",
                "RETARD_REPETE",
                "INSUBORDINATION",
                "MANQUE_DE_RESPECT",
                "NON_RESPECT_TENUE",
                "UTILISATION_TELEPHONE",
                "BAGARRE_VIOLENCE",
                "VOL",
                "COMPORTEMENT_IMMORAL",
                "NON_PAIEMENT_COTISATION",
                "NEGLIGENCE_MATERIEL",
                "BAVARDAGE_PENDANT_SERVICE",
                "RELATION_AMOUREUSE",
                "CONSOMMATION_STUPEFIANTS",
                "AGRESSION_PHYSIQUE_RESPONSABLE",
                "MENSONGE",
                "INFLUENCE_PARENTALE_INAPPROPRIEE",
                "AUTRE",
                name="offensecategory",
            ),
            nullable=False,
        ),
        sa.Column("offense_description", sa.String(length=2000), nullable=False),
        sa.Column(
            "offense_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "MINEUR",
                "MOYEN",
                "GRAVE",
                "TRES_GRAVE",
                name="sanctionseverity",
            ),
            nullable=False,
            server_default="MINEUR",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "SIGNALE",
                "CONVOQUE",
                "EN_AUDIENCE",
                "VERDICT_RENDU",
                "EXECUTE",
                "CLASSE",
                name="disciplinecasestatus",
            ),
            nullable=False,
            server_default="SIGNALE",
        ),
        sa.Column("convocation_date", sa.DateTime(), nullable=True),
        sa.Column("convocation_notes", sa.String(length=1000), nullable=True),
        sa.Column(
            "sanction_type",
            sa.Enum(
                "AUCUNE",
                "AVERTISSEMENT_VERBAL",
                "AVERTISSEMENT_ECRIT",
                "SUSPENSION_TEMPORAIRE",
                "EXCLUSION_DEFINITIVE",
                "LETTRE_EXCUSE",
                "CORVEE_INTENSIVE",
                "RECYCLAGE_SERVICE",
                name="sanctiontype",
            ),
            nullable=False,
            server_default="AUCUNE",
        ),
        sa.Column("verdict_notes", sa.String(length=2000), nullable=True),
        sa.Column("verdict_date", sa.DateTime(), nullable=True),
        sa.Column("verdict_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suspension_start", sa.DateTime(), nullable=True),
        sa.Column("suspension_end", sa.DateTime(), nullable=True),
        sa.Column("suspension_days", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["accused_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verdict_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discipline_cases_accused_user_id"),
        "discipline_cases",
        ["accused_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discipline_cases_offense_category"),
        "discipline_cases",
        ["offense_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discipline_cases_status"), "discipline_cases", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discipline_cases_status"), table_name="discipline_cases")
    op.drop_index(
        op.f("ix_discipline_cases_offense_category"), table_name="discipline_cases"
    )
    op.drop_index(
        op.f("ix_discipline_cases_accused_user_id"), table_name="discipline_cases"
    )
    op.drop_table("discipline_cases")

    sa.Enum(name="sanctiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="disciplinecasestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sanctionseverity").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="offensecategory").drop(op.get_bind(), checkfirst=True)
