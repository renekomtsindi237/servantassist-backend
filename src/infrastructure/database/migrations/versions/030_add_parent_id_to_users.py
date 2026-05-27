"""add parent_id to users for servant-parent link

Revision ID: 030
Revises: 029
Create Date: 2026-05-24
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_parent_id",
        "users",
        "users",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_parent_id", "users", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_users_parent_id", "users")
    op.drop_constraint("fk_users_parent_id", "users", type_="foreignkey")
    op.drop_column("users", "parent_id")
