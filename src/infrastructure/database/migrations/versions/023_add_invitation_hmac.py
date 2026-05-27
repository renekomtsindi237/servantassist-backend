"""add HMAC index columns to invitation_codes

Révision ID  : 023
Précédente   : 022
Date         : 2026-05-19

Objectif :
  Ajouter les colonnes d'index HMAC sur la table invitation_codes pour
  permettre les lookups exacts sur email et phone_number sans stocker
  ces valeurs en clair (Loi 2024/017 Cameroun, Art. 22).

  - email_hmac    : HMAC-SHA256(lowercase(email))
  - phone_hmac    : HMAC-SHA256(lowercase(phone_number))

NOTE migration des données existantes :
  Si des codes d'invitation en clair existent déjà en base (dev),
  exécutez le script utilitaire après la migration :
      python scripts/encrypt_existing_invitations.py
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invitation_codes",
        sa.Column("email_hmac", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "invitation_codes",
        sa.Column("phone_hmac", sa.String(length=64), nullable=True),
    )

    op.create_index(
        "ix_invitation_codes_email_hmac",
        "invitation_codes",
        ["email_hmac"],
        unique=False,
    )
    op.create_index(
        "ix_invitation_codes_phone_hmac",
        "invitation_codes",
        ["phone_hmac"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_invitation_codes_phone_hmac", table_name="invitation_codes")
    op.drop_index("ix_invitation_codes_email_hmac", table_name="invitation_codes")
    op.drop_column("invitation_codes", "phone_hmac")
    op.drop_column("invitation_codes", "email_hmac")
