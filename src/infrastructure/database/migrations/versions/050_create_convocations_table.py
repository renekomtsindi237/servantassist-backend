"""050 create convocations table

Formalise la convocation des parents (Art. 48-49 du reglement interieur) :
jusqu'ici le systeme ne faisait que calculer un indicateur sans jamais
enregistrer de convocation ni suivre de delai de reponse.

Revision ID: 050
Revises: 049
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "convocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("servant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motif", sa.String(length=32), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("convocation_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="EN_ATTENTE"
        ),
        sa.Column("convened_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("honored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("honored_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["servant_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["convened_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["honored_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_convocations_servant_id", "convocations", ["servant_id"])
    op.create_index("ix_convocations_status", "convocations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_convocations_status", table_name="convocations")
    op.drop_index("ix_convocations_servant_id", table_name="convocations")
    op.drop_table("convocations")
