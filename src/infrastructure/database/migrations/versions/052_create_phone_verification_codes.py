"""052 create phone verification codes

Vérification du numéro de téléphone à l'inscription Servant/Parent (OTP
WhatsApp) — aucun compte n'existe encore à ce stade, table indépendante de
password_reset_codes (voir 031) plutôt qu'un FK vers users.

Revision ID: 052
Revises: 051
Create Date: 2026-07-17
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_verification_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_hmac", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_token", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pvc_phone_hmac", "phone_verification_codes", ["phone_hmac"])
    op.create_index(
        "ix_pvc_verification_token",
        "phone_verification_codes",
        ["verification_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_pvc_verification_token", table_name="phone_verification_codes")
    op.drop_index("ix_pvc_phone_hmac", table_name="phone_verification_codes")
    op.drop_table("phone_verification_codes")
