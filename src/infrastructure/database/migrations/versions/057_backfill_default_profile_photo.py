"""057 backfill default profile photo for existing users

Applique la même contrainte que côté web (`public/profil.jpeg`, jusqu'ici
utilisé seulement comme repli d'affichage côté client) : tout utilisateur
sans photo de profil reçoit désormais une valeur réelle en base
(`{APP_URL}/static/images/profil.jpeg`), identique à ce que
`UserRepository.create()` (voir `default_profile_photo_url()`) applique
maintenant à la création — cette migration ne fait que rattraper les
comptes déjà existants. Un upload réel (`POST /users/me/photo`) écrase
cette valeur sans distinction.

Revision ID: 057
Revises: 056
Create Date: 2026-07-20
"""
import sqlalchemy as sa
from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def _default_photo_url() -> str:
    from src.infrastructure.config.settings import get_settings

    return f"{get_settings().APP_URL.rstrip('/')}/static/images/profil.jpeg"


def upgrade() -> None:
    url = _default_photo_url()
    op.execute(
        sa.text("UPDATE users SET profile_photo_url = :url WHERE profile_photo_url IS NULL").bindparams(url=url)
    )


def downgrade() -> None:
    url = _default_photo_url()
    op.execute(
        sa.text("UPDATE users SET profile_photo_url = NULL WHERE profile_photo_url = :url").bindparams(url=url)
    )
