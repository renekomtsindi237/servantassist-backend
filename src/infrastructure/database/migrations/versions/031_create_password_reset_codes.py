"""create password_reset_codes table for mobile OTP flow

Revision ID: 031
Revises: 030
Create Date: 2026-05-25
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prc_email", "password_reset_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_prc_email", "password_reset_codes")
    op.drop_table("password_reset_codes")
