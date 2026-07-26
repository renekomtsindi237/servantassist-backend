"""create api_keys table

Revision ID: 019
Revises: 018
Create Date: 2026-03-24 00:00:00.000000

Table : api_keys
  id            UUID PK
  name          VARCHAR(100) — label lisible (ex. "App Android Paroisse X")
  key_hash      VARCHAR(128) — bcrypt hash de la clé (jamais stockée en clair)
  user_id       FK → users.id — admin propriétaire de la clé
  scopes        JSON — liste de scopes autorisés (ex. ["read:events", "read:users"])
  is_active     BOOLEAN — permet la révocation sans suppression
  last_used_at  TIMESTAMP WITH TZ — mise à jour à chaque utilisation
  created_at    TIMESTAMP WITH TZ
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_is_active", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
