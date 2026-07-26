"""051 add oauth identity to users

Ajoute la connexion via Google (connexion uniquement, ne remplace pas
hashed_password). oauth_subject suit le meme schema de chiffrement que
email/phone_number (colonne chiffree + colonne HMAC pour la recherche,
Loi 2024/017 Art. 22). Colonnes generiques (oauth_provider/oauth_subject) :
pas de renommage necessaire si un autre fournisseur est ajoute plus tard.

Revision ID: 051
Revises: 050
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(length=16), nullable=True))
    op.add_column("users", sa.Column("oauth_subject", sa.String(), nullable=True))
    op.add_column("users", sa.Column("oauth_subject_hmac", sa.String(length=64), nullable=True))
    op.create_index("ix_users_oauth_subject_hmac", "users", ["oauth_subject_hmac"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_oauth_subject_hmac", table_name="users")
    op.drop_column("users", "oauth_subject_hmac")
    op.drop_column("users", "oauth_subject")
    op.drop_column("users", "oauth_provider")
