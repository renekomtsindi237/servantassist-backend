"""create council_meetings and council_attendances tables

Revision ID: 018
Revises: 017
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "council_meetings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("meeting_date", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("agenda", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_council_meetings_meeting_date"),
        "council_meetings",
        ["meeting_date"],
        unique=False,
    )

    op.create_table(
        "council_attendances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("responsable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PRESENT",
                "ABSENT",
                "EXCUSE",
                name="councilattendancestatus",
            ),
            nullable=False,
            server_default="PRESENT",
        ),
        sa.Column("excuse", sa.String(length=500), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["council_meetings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["responsable_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_council_attendances_meeting_id"),
        "council_attendances",
        ["meeting_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_council_attendances_responsable_id"),
        "council_attendances",
        ["responsable_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_council_attendances_responsable_id"), table_name="council_attendances"
    )
    op.drop_index(
        op.f("ix_council_attendances_meeting_id"), table_name="council_attendances"
    )
    op.drop_table("council_attendances")

    op.drop_index(
        op.f("ix_council_meetings_meeting_date"), table_name="council_meetings"
    )
    op.drop_table("council_meetings")

    sa.Enum(name="councilattendancestatus").drop(op.get_bind(), checkfirst=True)
