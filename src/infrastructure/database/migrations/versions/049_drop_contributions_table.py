"""049 drop legacy contributions table (superseded by cotisations)

Le module `contributions` est retire completement (code + schema) une fois
ses donnees migrees vers `cotisation_periods`/`member_cotisations` par la
migration 048. `cotisations` est desormais l'unique module actif.

Revision ID: 049
Revises: 048
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_contributions_servant_month_year", table_name="contributions")
    op.drop_index("idx_contributions_payment_mode", table_name="contributions")
    op.drop_index("idx_contributions_recorded_by", table_name="contributions")
    op.drop_index("idx_contributions_payment_date", table_name="contributions")
    op.drop_index("idx_contributions_month_year", table_name="contributions")
    op.drop_index("idx_contributions_servant_id", table_name="contributions")
    op.drop_table("contributions")


def downgrade() -> None:
    # Recreation du schema seul (cf. 003) — les donnees ne sont pas
    # restaurees depuis cotisation_periods/member_cotisations (transformation
    # non bijective : agregation des paiements hebdomadaires par mois).
    op.create_table(
        "contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("servant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("payment_mode", sa.String(20), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("week_number", sa.Integer, nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["servant_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount > 0", name="check_amount_positive"),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="check_month_valid"),
        sa.CheckConstraint("year >= 2020 AND year <= 2100", name="check_year_valid"),
        sa.CheckConstraint(
            "week_number IS NULL OR (week_number >= 1 AND week_number <= 4)",
            name="check_week_number_valid",
        ),
        sa.CheckConstraint(
            "(payment_mode = 'HEBDOMADAIRE' AND week_number IS NOT NULL) OR "
            "(payment_mode = 'MENSUEL' AND week_number IS NULL)",
            name="check_week_number_consistency",
        ),
    )
    op.create_index("idx_contributions_servant_id", "contributions", ["servant_id"])
    op.create_index("idx_contributions_month_year", "contributions", ["month", "year"])
    op.create_index("idx_contributions_payment_date", "contributions", ["payment_date"])
    op.create_index("idx_contributions_recorded_by", "contributions", ["recorded_by"])
    op.create_index("idx_contributions_payment_mode", "contributions", ["payment_mode"])
    op.create_index(
        "idx_contributions_servant_month_year",
        "contributions",
        ["servant_id", "month", "year"],
    )
