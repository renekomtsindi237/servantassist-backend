"""create material tables

Revision ID: 008
Revises: 007
Create Date: 2026-02-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table material_items ──────────────────────────────────────────
    op.create_table(
        "material_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("condition", sa.String(length=50), nullable=False, server_default="BON"),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("purchase_date", sa.DateTime(), nullable=True),
        sa.Column("last_maintenance_date", sa.DateTime(), nullable=True),
        sa.Column("next_maintenance_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity >= 0", name="check_quantity_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_material_items_category", "material_items", ["category"])
    op.create_index("idx_material_items_condition", "material_items", ["condition"])
    op.create_index("idx_material_items_created_by", "material_items", ["created_by"])

    # ── Table cleaning_tasks ──────────────────────────────────────────
    op.create_table(
        "cleaning_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("scheduled_date", sa.DateTime(), nullable=False),
        sa.Column("scheduled_time", sa.String(length=10), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PLANIFIEE"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.Column("validated_by", sa.UUID(), nullable=True),
        sa.Column("photos_before", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("photos_after", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_cleaning_tasks_type", "cleaning_tasks", ["task_type"])
    op.create_index("idx_cleaning_tasks_status", "cleaning_tasks", ["status"])
    op.create_index("idx_cleaning_tasks_date", "cleaning_tasks", ["scheduled_date"])
    op.create_index("idx_cleaning_tasks_created_by", "cleaning_tasks", ["created_by"])

    # ── Table task_assignments ────────────────────────────────────────
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("servant_id", sa.UUID(), nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["cleaning_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["servant_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "servant_id", name="uq_task_servant"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_task_assignments_task", "task_assignments", ["task_id"])
    op.create_index("idx_task_assignments_servant", "task_assignments", ["servant_id"])

    # ── Table aube_tasks ──────────────────────────────────────────────
    op.create_table(
        "aube_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("scheduled_date", sa.DateTime(), nullable=False),
        sa.Column("scheduled_time", sa.String(length=10), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("aube_count", sa.Integer(), nullable=False),
        sa.Column("aube_sizes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PLANIFIEE"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.Column("validated_by", sa.UUID(), nullable=True),
        sa.Column("photos_before", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("photos_after", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "broadcast_notification",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("aube_count > 0", name="check_aube_count_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_aube_tasks_type", "aube_tasks", ["task_type"])
    op.create_index("idx_aube_tasks_status", "aube_tasks", ["status"])
    op.create_index("idx_aube_tasks_date", "aube_tasks", ["scheduled_date"])
    op.create_index("idx_aube_tasks_created_by", "aube_tasks", ["created_by"])

    # ── Table maintenance_history ─────────────────────────────────────
    op.create_table(
        "maintenance_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("maintenance_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("performed_date", sa.DateTime(), nullable=False),
        sa.Column("performed_by", sa.UUID(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["item_id"], ["material_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cost >= 0", name="check_cost_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_maintenance_history_item", "maintenance_history", ["item_id"])
    op.create_index("idx_maintenance_history_date", "maintenance_history", ["performed_date"])
    op.create_index("idx_maintenance_history_performed_by", "maintenance_history", ["performed_by"])


def downgrade() -> None:
    # Supprimer les tables dans l'ordre inverse
    op.drop_table("maintenance_history")
    op.drop_table("aube_tasks")
    op.drop_table("task_assignments")
    op.drop_table("cleaning_tasks")
    op.drop_table("material_items")
