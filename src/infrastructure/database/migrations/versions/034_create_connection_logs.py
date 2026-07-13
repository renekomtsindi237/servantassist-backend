"""034 create connection_logs table for IP geolocation

Revision ID: 034
Revises: 033
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connection_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
        ),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connection_logs_logged_at", "connection_logs", ["logged_at"])


def downgrade() -> None:
    op.drop_index("ix_connection_logs_logged_at", "connection_logs")
    op.drop_table("connection_logs")
