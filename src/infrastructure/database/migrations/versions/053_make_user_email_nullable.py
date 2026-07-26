"""053 make user email nullable

L'email n'est plus auto-généré pour SERVANT/PARENT sans email fourni —
NULL réel plutôt qu'une valeur technique factice. L'identité du JWT repose
désormais sur users.id (voir AuthService.create_tokens), plus sur l'email,
ce qui rend cette colonne sûre à rendre optionnelle pour tous les rôles.
L'index unique existant (ix_users_email) reste valide : Postgres autorise
plusieurs NULL dans un index unique.

Revision ID: 053
Revises: 052
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
