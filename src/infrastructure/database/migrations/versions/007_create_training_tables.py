"""create training tables

Revision ID: 007
Revises: 006
Create Date: 2026-02-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table training_sessions ──────────────────────────────────────
    op.create_table(
        "training_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("objectives", sa.Text(), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("start_time", sa.String(length=10), nullable=False),
        sa.Column("end_time", sa.String(length=10), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("trainer_id", sa.UUID(), nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="PLANIFIEE"
        ),
        sa.Column("materials_url", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(["trainer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("duration_minutes > 0", name="check_duration_positive"),
        sa.CheckConstraint(
            "max_participants >= 0", name="check_max_participants_positive"
        ),
    )

    # Index pour améliorer les performances
    op.create_index("idx_training_sessions_date", "training_sessions", ["date"])
    op.create_index("idx_training_sessions_level", "training_sessions", ["level"])
    op.create_index("idx_training_sessions_status", "training_sessions", ["status"])
    op.create_index(
        "idx_training_sessions_trainer", "training_sessions", ["trainer_id"]
    )
    op.create_index(
        "idx_training_sessions_created_by", "training_sessions", ["created_by"]
    )

    # ── Table training_participations ────────────────────────────────
    op.create_table(
        "training_participations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("servant_id", sa.UUID(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="INSCRIT"
        ),
        sa.Column(
            "registration_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("attendance_marked_at", sa.DateTime(), nullable=True),
        sa.Column("evaluation_score", sa.Integer(), nullable=True),
        sa.Column("evaluation_comments", sa.Text(), nullable=True),
        sa.Column(
            "certificate_issued", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("certificate_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("registered_by", sa.UUID(), nullable=False),
        sa.Column("marked_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["session_id"], ["training_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["servant_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registered_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "evaluation_score >= 0 AND evaluation_score <= 100",
            name="check_score_range",
        ),
        sa.UniqueConstraint("session_id", "servant_id", name="uq_session_servant"),
    )

    # Index pour améliorer les performances
    op.create_index(
        "idx_training_participations_session", "training_participations", ["session_id"]
    )
    op.create_index(
        "idx_training_participations_servant", "training_participations", ["servant_id"]
    )
    op.create_index(
        "idx_training_participations_status", "training_participations", ["status"]
    )

    # ── Table training_materials ─────────────────────────────────────
    op.create_table(
        "training_materials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=False, server_default="TOUS"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("file_size > 0", name="check_file_size_positive"),
        sa.CheckConstraint("view_count >= 0", name="check_view_count_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_training_materials_type", "training_materials", ["type"])
    op.create_index("idx_training_materials_level", "training_materials", ["level"])
    op.create_index(
        "idx_training_materials_public", "training_materials", ["is_public"]
    )
    op.create_index(
        "idx_training_materials_uploaded_by", "training_materials", ["uploaded_by"]
    )

    # ── Table session_materials ──────────────────────────────────────
    op.create_table(
        "session_materials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["training_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["training_materials.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "material_id", name="uq_session_material"),
    )

    # Index pour améliorer les performances
    op.create_index(
        "idx_session_materials_session", "session_materials", ["session_id"]
    )
    op.create_index(
        "idx_session_materials_material", "session_materials", ["material_id"]
    )


def downgrade() -> None:
    # Supprimer les tables dans l'ordre inverse
    op.drop_table("session_materials")
    op.drop_table("training_materials")
    op.drop_table("training_participations")
    op.drop_table("training_sessions")
