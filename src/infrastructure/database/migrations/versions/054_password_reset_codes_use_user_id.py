"""054 password reset codes use user_id

password_reset_codes était clé sur `email` (y compris pour le flow
téléphone, qui réutilisait l'email technique auto-généré comme clé interne).
Cette table est désormais clé sur user_id, seul identifiant garanti présent
maintenant que l'email est réellement optionnel pour SERVANT/PARENT (voir
migration 053). Table vidée au passage : les codes OTP existants ont une
durée de vie de 15 minutes, aucune perte de données significative.

Revision ID: 054
Revises: 053
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM password_reset_codes")
    op.drop_index("ix_prc_email", table_name="password_reset_codes")
    op.drop_column("password_reset_codes", "email")
    op.add_column("password_reset_codes", sa.Column("user_id", UUID(as_uuid=True), nullable=False))
    op.create_index("ix_prc_user_id", "password_reset_codes", ["user_id"])


def downgrade() -> None:
    op.execute("DELETE FROM password_reset_codes")
    op.drop_index("ix_prc_user_id", table_name="password_reset_codes")
    op.drop_column("password_reset_codes", "user_id")
    op.add_column("password_reset_codes", sa.Column("email", sa.String(255), nullable=False))
    op.create_index("ix_prc_email", "password_reset_codes", ["email"])
