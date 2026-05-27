"""create notifications and notification_preferences tables

Revision ID: 013
Revises: 012
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(
                "AFFECTATION",
                "RAPPEL_EVENEMENT",
                "ABSENCE_PARENT",
                "DISCIPLINE",
                "COTISATION",
                "NOMINATION",
                "GENERAL",
                name="notificationtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum("EMAIL", "WHATSAPP", "IN_APP", name="notificationchannel"),
            nullable=False,
            server_default="IN_APP",
        ),
        sa.Column(
            "priority",
            sa.Enum("LOW", "NORMAL", "HIGH", "URGENT", name="notificationpriority"),
            nullable=False,
            server_default="NORMAL",
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.String(length=5000), nullable=False),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "SENT",
                "DELIVERED",
                "READ",
                "FAILED",
                name="notificationstatus",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("broadcast_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_recipient_id"), "notifications", ["recipient_id"], unique=False)
    op.create_index(op.f("ix_notifications_notification_type"), "notifications", ["notification_type"], unique=False)
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"], unique=False)
    op.create_index(op.f("ix_notifications_broadcast_id"), "notifications", ["broadcast_id"], unique=False)

    op.create_table(
        "notification_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(
                "AFFECTATION",
                "RAPPEL_EVENEMENT",
                "ABSENCE_PARENT",
                "DISCIPLINE",
                "COTISATION",
                "NOMINATION",
                "GENERAL",
                name="notificationtype",
                create_constraint=False,  # already created above
            ),
            nullable=False,
        ),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "notification_type", name="uq_notif_pref_user_type"),
    )
    op.create_index(op.f("ix_notification_preferences_user_id"), "notification_preferences", ["user_id"], unique=False)
    op.create_index(op.f("ix_notification_preferences_notification_type"), "notification_preferences", ["notification_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_preferences_notification_type"), table_name="notification_preferences")
    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index(op.f("ix_notifications_broadcast_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_notification_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_recipient_id"), table_name="notifications")
    op.drop_table("notifications")

    sa.Enum(name="notificationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notificationpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notificationchannel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notificationtype").drop(op.get_bind(), checkfirst=True)
