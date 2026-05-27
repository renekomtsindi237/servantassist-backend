"""create attendances table

Revision ID: 021
Revises: 020
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attendance_type", sa.String(length=17), nullable=False),
        sa.Column("attendance_date", sa.DateTime(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=15), nullable=False),
        sa.Column("justification", sa.String(length=1000), nullable=True),
        sa.Column("justified_at", sa.DateTime(), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_attendances_user_id", "attendances", ["user_id"])
    op.create_index("ix_attendances_event_id", "attendances", ["event_id"])
    op.create_index(
        "ix_attendances_attendance_type", "attendances", ["attendance_type"]
    )
    op.create_index(
        "ix_attendances_attendance_date", "attendances", ["attendance_date"]
    )
    op.create_index("ix_attendances_status", "attendances", ["status"])


def downgrade() -> None:
    op.drop_index("ix_attendances_status", table_name="attendances")
    op.drop_index("ix_attendances_attendance_date", table_name="attendances")
    op.drop_index("ix_attendances_attendance_type", table_name="attendances")
    op.drop_index("ix_attendances_event_id", table_name="attendances")
    op.drop_index("ix_attendances_user_id", table_name="attendances")
    op.drop_table("attendances")
