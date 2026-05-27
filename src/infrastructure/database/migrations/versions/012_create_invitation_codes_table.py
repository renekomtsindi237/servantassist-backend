"""create invitation_codes table

Revision ID: 012
Revises: 011
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invitation_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="PARENT"),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACCEPTED", "REVOKED", name="invitationstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("used_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "whatsapp_sent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitation_codes_code"), "invitation_codes", ["code"], unique=True)
    op.create_index(op.f("ix_invitation_codes_status"), "invitation_codes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invitation_codes_status"), table_name="invitation_codes")
    op.drop_index(op.f("ix_invitation_codes_code"), table_name="invitation_codes")
    op.drop_table("invitation_codes")

    sa.Enum(name="invitationstatus").drop(op.get_bind(), checkfirst=True)
