"""expand PII column sizes to accommodate AES-256-GCM encrypted values

Revision ID: 026
Revises: 025
Create Date: 2026-05-23

VARCHAR(20) for phone_number is too small for encrypted values (~50-100 chars).
Also expand first_name and last_name to be safe.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "phone_number",
        type_=sa.String(length=500),
        existing_type=sa.String(length=20),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "first_name",
        type_=sa.String(length=500),
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "last_name",
        type_=sa.String(length=500),
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "phone_number",
        type_=sa.String(length=20),
        existing_type=sa.String(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "first_name",
        type_=sa.String(length=100),
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "last_name",
        type_=sa.String(length=100),
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )
