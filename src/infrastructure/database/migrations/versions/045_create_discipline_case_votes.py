"""045 create discipline_case_votes (conseil de discipline a quorum)

Le reglement interieur (Art. 16-17) prevoit un conseil de discipline
collegial (Delegue+adjoint, Secretaire General+adjoint, Censeur+adjoint,
Ceremoniaire) qui doit deliberer avant qu'un verdict ne soit rendu. Cette
table trace le vote de chaque siege sur un dossier disciplinaire.

Revision ID: 045
Revises: 044
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discipline_case_votes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poste", sa.String(length=64), nullable=False),
        sa.Column("voter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "sanction_type",
            # postgresql.ENUM (pas sa.Enum generique) est necessaire pour que
            # create_type=False soit reellement respecte par op.create_table :
            # sa.Enum generique reemet un CREATE TYPE malgre le flag des que la
            # migration tourne dans un nouveau process (ex. prod deja a la
            # revision 040, redemarree pour appliquer 041+) meme si le meme
            # scenario passe inapercu sur une DB vide migree en un seul run.
            postgresql.ENUM(
                "AUCUNE",
                "AVERTISSEMENT_VERBAL",
                "AVERTISSEMENT_ECRIT",
                "SUSPENSION_TEMPORAIRE",
                "EXCLUSION_DEFINITIVE",
                "LETTRE_EXCUSE",
                "CORVEE_INTENSIVE",
                "RECYCLAGE_SERVICE",
                name="sanctiontype",
                create_type=False,  # reutilise le type Postgres cree par la migration 015
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("voted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["case_id"], ["discipline_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "poste", name="uq_discipline_vote_case_poste"),
    )
    op.create_index(
        op.f("ix_discipline_case_votes_case_id"), "discipline_case_votes", ["case_id"]
    )
    op.create_index(
        op.f("ix_discipline_case_votes_poste"), "discipline_case_votes", ["poste"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discipline_case_votes_poste"), table_name="discipline_case_votes")
    op.drop_index(op.f("ix_discipline_case_votes_case_id"), table_name="discipline_case_votes")
    op.drop_table("discipline_case_votes")
