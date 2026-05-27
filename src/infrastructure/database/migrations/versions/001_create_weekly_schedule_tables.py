"""create weekly schedule tables

Revision ID: 001
Revises: 000
Create Date: 2026-02-10 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = "000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Créer la table weekly_schedule_templates
    op.create_table(
        "weekly_schedule_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "watermark_logo_url",
            sa.String(length=500),
            nullable=False,
            server_default="logo_servant.jpeg",
        ),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weekly_schedule_templates_start_date"),
        "weekly_schedule_templates",
        ["start_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weekly_schedule_templates_status"),
        "weekly_schedule_templates",
        ["status"],
        unique=False,
    )

    # Créer la table weekly_schedule_slots
    op.create_table(
        "weekly_schedule_slots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.String(length=20), nullable=False),
        sa.Column("mass_time", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["weekly_schedule_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weekly_schedule_slots_template_id"),
        "weekly_schedule_slots",
        ["template_id"],
        unique=False,
    )

    # Créer la table slot_servant_assignments (many-to-many)
    op.create_table(
        "slot_servant_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slot_id", sa.UUID(), nullable=False),
        sa.Column("servant_id", sa.UUID(), nullable=True),
        sa.Column("servant_name", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("assigned_by", sa.UUID(), nullable=False),
        sa.Column("last_modified_by", sa.UUID(), nullable=True),
        sa.Column("presence_marked_by", sa.UUID(), nullable=True),
        sa.Column("presence_marked_at", sa.DateTime(), nullable=True),
        sa.Column("is_present", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["weekly_schedule_slots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["servant_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["last_modified_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["presence_marked_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_slot_servant_assignments_slot_id"),
        "slot_servant_assignments",
        ["slot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_slot_servant_assignments_servant_id"),
        "slot_servant_assignments",
        ["servant_id"],
        unique=False,
    )

    # Créer la table weekly_schedule_modification_logs
    op.create_table(
        "weekly_schedule_modification_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("slot_id", sa.UUID(), nullable=True),
        sa.Column("assignment_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("modified_by", sa.UUID(), nullable=False),
        sa.Column("modified_by_name", sa.String(length=200), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("old_value", sa.String(length=1000), nullable=True),
        sa.Column("new_value", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"], ["weekly_schedule_templates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["weekly_schedule_slots.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["slot_servant_assignments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["modified_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weekly_schedule_modification_logs_template_id"),
        "weekly_schedule_modification_logs",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weekly_schedule_modification_logs_modified_by"),
        "weekly_schedule_modification_logs",
        ["modified_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weekly_schedule_modification_logs_modified_at"),
        "weekly_schedule_modification_logs",
        ["modified_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_weekly_schedule_modification_logs_modified_at"),
        table_name="weekly_schedule_modification_logs",
    )
    op.drop_index(
        op.f("ix_weekly_schedule_modification_logs_modified_by"),
        table_name="weekly_schedule_modification_logs",
    )
    op.drop_index(
        op.f("ix_weekly_schedule_modification_logs_template_id"),
        table_name="weekly_schedule_modification_logs",
    )
    op.drop_table("weekly_schedule_modification_logs")
    op.drop_index(
        op.f("ix_slot_servant_assignments_servant_id"),
        table_name="slot_servant_assignments",
    )
    op.drop_index(
        op.f("ix_slot_servant_assignments_slot_id"),
        table_name="slot_servant_assignments",
    )
    op.drop_table("slot_servant_assignments")
    op.drop_index(
        op.f("ix_weekly_schedule_slots_template_id"), table_name="weekly_schedule_slots"
    )
    op.drop_table("weekly_schedule_slots")
    op.drop_index(
        op.f("ix_weekly_schedule_templates_status"),
        table_name="weekly_schedule_templates",
    )
    op.drop_index(
        op.f("ix_weekly_schedule_templates_start_date"),
        table_name="weekly_schedule_templates",
    )
    op.drop_table("weekly_schedule_templates")
