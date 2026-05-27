"""create cotisation_periods and member_cotisations tables

Revision ID: 014
Revises: 013
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cotisation_periods",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "cotisation_type",
            sa.Enum(
                "ORDINAIRE",
                "SPECIALE",
                "AMENDE",
                "AUTRE",
                name="cotisationtype",
            ),
            nullable=False,
            server_default="ORDINAIRE",
        ),
        sa.Column(
            "period_type",
            sa.Enum(
                "HEBDOMADAIRE",
                "MENSUEL",
                "EVENEMENT",
                "ANNUEL",
                "PONCTUEL",
                name="periodtype",
            ),
            nullable=False,
            server_default="MENSUEL",
        ),
        sa.Column("amount_expected", sa.Float(), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cotisation_periods_cotisation_type"),
        "cotisation_periods",
        ["cotisation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cotisation_periods_is_active"),
        "cotisation_periods",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "member_cotisations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_paid", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "EN_ATTENTE",
                "PAYE",
                "PAYE_PARTIELLEMENT",
                "EXONERE",
                "EN_RETARD",
                name="cotisationstatus",
            ),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
        sa.Column("payment_date", sa.DateTime(), nullable=True),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["period_id"], ["cotisation_periods.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_member_cotisations_period_id"),
        "member_cotisations",
        ["period_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_member_cotisations_user_id"),
        "member_cotisations",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_member_cotisations_user_id"), table_name="member_cotisations"
    )
    op.drop_index(
        op.f("ix_member_cotisations_period_id"), table_name="member_cotisations"
    )
    op.drop_table("member_cotisations")

    op.drop_index(
        op.f("ix_cotisation_periods_is_active"), table_name="cotisation_periods"
    )
    op.drop_index(
        op.f("ix_cotisation_periods_cotisation_type"), table_name="cotisation_periods"
    )
    op.drop_table("cotisation_periods")

    sa.Enum(name="cotisationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="periodtype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="cotisationtype").drop(op.get_bind(), checkfirst=True)
