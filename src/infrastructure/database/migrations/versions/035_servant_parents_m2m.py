"""many-to-many servant_parents — replace parent_id FK on users

Revision ID: 035
Revises: 034
Create Date: 2026-05-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "servant_parents",
        sa.Column("servant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("servant_id", "parent_id", name="pk_servant_parents"),
        sa.ForeignKeyConstraint(
            ["servant_id"], ["users.id"], name="fk_sp_servant", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["users.id"], name="fk_sp_parent", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_servant_parents_servant", "servant_parents", ["servant_id"])
    op.create_index("ix_servant_parents_parent", "servant_parents", ["parent_id"])

    # Backfill depuis la colonne parent_id existante sur users
    op.execute(
        """
        INSERT INTO servant_parents (servant_id, parent_id, created_at)
        SELECT id, parent_id, COALESCE(created_at, NOW())
        FROM users
        WHERE parent_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Supprimer l'ancienne colonne parent_id
    op.drop_constraint("fk_users_parent_id", "users", type_="foreignkey")
    op.drop_index("ix_users_parent_id", "users")
    op.drop_column("users", "parent_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("parent_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_parent_id", "users", "users", ["parent_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_users_parent_id", "users", ["parent_id"])

    # Restaurer 1 parent par servant (le premier lié)
    op.execute(
        """
        UPDATE users u
        SET parent_id = (
            SELECT parent_id FROM servant_parents sp
            WHERE sp.servant_id = u.id
            ORDER BY sp.created_at
            LIMIT 1
        )
        WHERE EXISTS (SELECT 1 FROM servant_parents sp WHERE sp.servant_id = u.id)
        """
    )

    op.drop_index("ix_servant_parents_parent", "servant_parents")
    op.drop_index("ix_servant_parents_servant", "servant_parents")
    op.drop_table("servant_parents")
