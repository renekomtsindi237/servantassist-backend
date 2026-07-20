"""044 add approval fields to poste_actions (Econome -> Aumonier)

Le reglement interieur (section Econome) exige que toute sortie de fonds
soit operee "sous le controle et l'accord de l'Aumonier". Ajoute les champs
necessaires pour tracer cette approbation sur les actions de categorie
DEPENSE.

Revision ID: 044
Revises: 043
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "poste_actions",
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "poste_actions",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_poste_actions_approved_by",
        "poste_actions",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_poste_actions_approved_by", "poste_actions", type_="foreignkey")
    op.drop_column("poste_actions", "approved_at")
    op.drop_column("poste_actions", "approved_by")
