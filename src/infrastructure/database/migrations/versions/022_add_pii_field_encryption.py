"""add PII field encryption indexes (email_hmac, phone_hmac)

Révision ID  : 022
Précédente   : 021
Date         : 2026-05-19

Objectif :
  Ajouter les colonnes d'index HMAC nécessaires au chiffrement des données
  personnelles (Loi 2024/017 du Cameroun sur la protection des données).

  - email_hmac    : HMAC-SHA256(lowercase(email))    — remplace l'index SQL
                    direct sur email pour les lookups get_by_email()
  - phone_hmac    : HMAC-SHA256(lowercase(phone))    — idem pour get_by_phone()

  Les colonnes email, phone_number, first_name, last_name, birth_date,
  baptism_date continuent d'exister mais seront désormais remplies par le
  backend avec des blobs AES-256-GCM encodés en base64url.

NOTE migration des données existantes :
  Si des données en clair existent déjà en base (environnement de dev),
  exécutez le script utilitaire après la migration :
      python scripts/encrypt_existing_users.py
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_hmac", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("phone_hmac", sa.String(length=64), nullable=True),
    )

    op.create_index("ix_users_email_hmac", "users", ["email_hmac"], unique=False)
    op.create_index("ix_users_phone_hmac", "users", ["phone_hmac"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_phone_hmac", table_name="users")
    op.drop_index("ix_users_email_hmac", table_name="users")
    op.drop_column("users", "phone_hmac")
    op.drop_column("users", "email_hmac")
