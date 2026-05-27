"""create assignments table

Revision ID: 011
Revises: 010
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "liturgical_role",
            sa.Enum(
                "CRUCIFER",
                "THURIFER",
                "ACOLYTE",
                "CEROMONIAIRE",
                "NAVETTIER",
                "PORTE_MITRE",
                "PORTE_CROSSE",
                "PORTE_BOUGEOIR",
                "LECTEUR",
                "SERVANT_GENERAL",
                "AUTRE",
                name="liturgicalrole",
            ),
            nullable=False,
            server_default="SERVANT_GENERAL",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "DECLINED",
                "PRESENT",
                "ABSENT",
                "CANCELLED",
                name="assignmentstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        # Un servant ne peut avoir qu'une seule affectation par evenement
        sa.UniqueConstraint("event_id", "user_id", name="uq_assignment_event_user"),
    )
    op.create_index(op.f("ix_assignments_event_id"), "assignments", ["event_id"], unique=False)
    op.create_index(op.f("ix_assignments_user_id"), "assignments", ["user_id"], unique=False)
    op.create_index(op.f("ix_assignments_status"), "assignments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assignments_status"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_user_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_event_id"), table_name="assignments")
    op.drop_table("assignments")

    sa.Enum(name="assignmentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="liturgicalrole").drop(op.get_bind(), checkfirst=True)
