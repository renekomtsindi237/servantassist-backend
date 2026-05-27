"""create events and event_participants tables

Revision ID: 010
Revises: 009
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "MESSE_DOMINICALE",
                "MESSE_SEMAINE",
                "MESSE_PONTIFICALE",
                "MESSE_SOLENNELLE_PONTIFICALE",
                "MESSE_ACTION_GRACE",
                "MARIAGE",
                "REQUIEM",
                "RECOLLECTION",
                "CAMP_SPIRITUEL",
                "JOURNEE_AMITIE",
                "JOURNEE_SPORTIVE",
                "CAMP",
                "REPETITION",
                "AUTRE",
                name="eventtype",
            ),
            nullable=False,
            server_default="MESSE_DOMINICALE",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "BROUILLON",
                "PUBLIE",
                "EN_COURS",
                "TERMINE",
                "ANNULE",
                name="eventstatus",
            ),
            nullable=False,
            server_default="BROUILLON",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"], unique=False)
    op.create_index(op.f("ix_events_status"), "events", ["status"], unique=False)
    op.create_index(op.f("ix_events_start_time"), "events", ["start_time"], unique=False)

    op.create_table(
        "event_participants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "participant_role",
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
                "SERVANT",
                "PARTICIPANT",
                "AUTRE",
                name="participantrole",
            ),
            nullable=False,
            server_default="SERVANT",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "INVITE",
                "CONFIRME",
                "DECLINE",
                "PRESENT",
                "ABSENT",
                name="participantstatus",
            ),
            nullable=False,
            server_default="INVITE",
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_participants_event_id"), "event_participants", ["event_id"], unique=False)
    op.create_index(op.f("ix_event_participants_user_id"), "event_participants", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_event_participants_user_id"), table_name="event_participants")
    op.drop_index(op.f("ix_event_participants_event_id"), table_name="event_participants")
    op.drop_table("event_participants")

    op.drop_index(op.f("ix_events_start_time"), table_name="events")
    op.drop_index(op.f("ix_events_status"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_table("events")

    sa.Enum(name="participantstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="participantrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=True)
