"""create reports tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-10 12:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("report_date", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column(
            "participants", postgresql.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column("decisions", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="BROUILLON"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )

    # Index pour améliorer les performances
    op.create_index("ix_reports_type", "reports", ["type"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_report_date", "reports", ["report_date"])
    op.create_index("ix_reports_created_by", "reports", ["created_by"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])

    # Table report_attachments
    op.create_table(
        "report_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
    )

    # Index pour les pièces jointes
    op.create_index(
        "ix_report_attachments_report_id", "report_attachments", ["report_id"]
    )
    op.create_index(
        "ix_report_attachments_uploaded_by", "report_attachments", ["uploaded_by"]
    )


def downgrade() -> None:
    op.drop_index("ix_report_attachments_uploaded_by", table_name="report_attachments")
    op.drop_index("ix_report_attachments_report_id", table_name="report_attachments")
    op.drop_table("report_attachments")

    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_created_by", table_name="reports")
    op.drop_index("ix_reports_report_date", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_type", table_name="reports")
    op.drop_table("reports")
