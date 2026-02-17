"""create sport culture tables

Revision ID: 009
Revises: 008
Create Date: 2026-02-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table sport_culture_events ────────────────────────────────────
    op.create_table(
        "sport_culture_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("sport_type", sa.String(length=50), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("start_time", sa.String(length=10), nullable=False),
        sa.Column("end_time", sa.String(length=10), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PLANIFIE"),
        sa.Column("registration_deadline", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photos", sa.JSON(), nullable=False, server_default="[]"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("max_participants >= 0", name="check_max_participants_positive"),
        sa.CheckConstraint("cost >= 0", name="check_cost_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_sport_culture_events_type", "sport_culture_events", ["event_type"])
    op.create_index("idx_sport_culture_events_status", "sport_culture_events", ["status"])
    op.create_index("idx_sport_culture_events_date", "sport_culture_events", ["date"])
    op.create_index("idx_sport_culture_events_created_by", "sport_culture_events", ["created_by"])

    # ── Table event_participations ────────────────────────────────────
    op.create_table(
        "event_participations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("servant_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="INSCRIT"),
        sa.Column(
            "registration_date",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("attendance_marked_at", sa.DateTime(), nullable=True),
        sa.Column("payment_status", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("payment_date", sa.DateTime(), nullable=True),
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
        sa.ForeignKeyConstraint(["event_id"], ["sport_culture_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["servant_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registered_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "servant_id", name="uq_event_servant"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_event_participations_event", "event_participations", ["event_id"])
    op.create_index("idx_event_participations_servant", "event_participations", ["servant_id"])
    op.create_index("idx_event_participations_status", "event_participations", ["status"])

    # ── Table event_results ───────────────────────────────────────────
    op.create_table(
        "event_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("result_type", sa.String(length=50), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("opponent_name", sa.String(length=100), nullable=True),
        sa.Column("opponent_score", sa.Integer(), nullable=True),
        sa.Column("ranking", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["event_id"], ["sport_culture_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("score >= 0", name="check_score_positive"),
        sa.CheckConstraint("opponent_score >= 0", name="check_opponent_score_positive"),
        sa.CheckConstraint("ranking >= 1", name="check_ranking_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_event_results_event", "event_results", ["event_id"])
    op.create_index("idx_event_results_recorded_by", "event_results", ["recorded_by"])

    # ── Table event_teams ─────────────────────────────────────────────
    op.create_table(
        "event_teams",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("captain_id", sa.UUID(), nullable=False),
        sa.Column("members", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["event_id"], ["sport_culture_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["captain_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index pour améliorer les performances
    op.create_index("idx_event_teams_event", "event_teams", ["event_id"])
    op.create_index("idx_event_teams_captain", "event_teams", ["captain_id"])


def downgrade() -> None:
    # Supprimer les tables dans l'ordre inverse
    op.drop_table("event_teams")
    op.drop_table("event_results")
    op.drop_table("event_participations")
    op.drop_table("sport_culture_events")
