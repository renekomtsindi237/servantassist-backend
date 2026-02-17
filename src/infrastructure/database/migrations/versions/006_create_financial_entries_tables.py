"""create financial entries tables

Revision ID: 006
Revises: 005
Create Date: 2026-02-10 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table financial_entries
    op.create_table(
        "financial_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(50),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
        sa.Column("verification_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "watermark_logo",
            sa.String(255),
            nullable=False,
            server_default="logo_servant.jpeg",
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("amount > 0", name="check_amount_positive"),
    )

    # Index pour améliorer les performances
    op.create_index("ix_financial_entries_date", "financial_entries", ["date"])
    op.create_index("ix_financial_entries_category", "financial_entries", ["category"])
    op.create_index("ix_financial_entries_source", "financial_entries", ["source"])
    op.create_index(
        "ix_financial_entries_verification_status",
        "financial_entries",
        ["verification_status"],
    )
    op.create_index("ix_financial_entries_recorded_by", "financial_entries", ["recorded_by"])
    op.create_index("ix_financial_entries_verified_by", "financial_entries", ["verified_by"])
    op.create_index("ix_financial_entries_created_at", "financial_entries", ["created_at"])

    # Table discrepancies
    op.create_table(
        "discrepancies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=True),
        sa.Column("actual_amount", sa.Float(), nullable=True),
        sa.Column("detected_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["entry_id"], ["financial_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["detected_by"], ["users.id"], ondelete="CASCADE"),
    )

    # Index pour les écarts
    op.create_index("ix_discrepancies_entry_id", "discrepancies", ["entry_id"])
    op.create_index("ix_discrepancies_detected_by", "discrepancies", ["detected_by"])
    op.create_index("ix_discrepancies_resolved", "discrepancies", ["resolved"])
    op.create_index("ix_discrepancies_detected_at", "discrepancies", ["detected_at"])


def downgrade() -> None:
    op.drop_index("ix_discrepancies_detected_at", table_name="discrepancies")
    op.drop_index("ix_discrepancies_resolved", table_name="discrepancies")
    op.drop_index("ix_discrepancies_detected_by", table_name="discrepancies")
    op.drop_index("ix_discrepancies_entry_id", table_name="discrepancies")
    op.drop_table("discrepancies")

    op.drop_index("ix_financial_entries_created_at", table_name="financial_entries")
    op.drop_index("ix_financial_entries_verified_by", table_name="financial_entries")
    op.drop_index("ix_financial_entries_recorded_by", table_name="financial_entries")
    op.drop_index("ix_financial_entries_verification_status", table_name="financial_entries")
    op.drop_index("ix_financial_entries_source", table_name="financial_entries")
    op.drop_index("ix_financial_entries_category", table_name="financial_entries")
    op.drop_index("ix_financial_entries_date", table_name="financial_entries")
    op.drop_table("financial_entries")
