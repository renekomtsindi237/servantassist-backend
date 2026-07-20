"""055 add AVERTISSEMENT_ABSENCE and CONVOCATION_PARENT to notificationtype enum

Ces deux valeurs existent dans l'enum Python `NotificationType`
(src/core/entities/notification.py, alerte 3 absences -> servant et
convocation 5 absences -> parent) mais n'avaient jamais été ajoutées au type
Postgres natif `notificationtype` — toute tentative d'envoyer une notification
de ce type (ex. marquer une présence ABSENT) échoue avec
`InvalidTextRepresentationError`. Écart préexistant, pas spécifique à un
environnement (reproductible en local comme en staging/production).

Revision ID: 055
Revises: 054
Create Date: 2026-07-19
"""
import sqlalchemy as sa

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'AVERTISSEMENT_ABSENCE'"))
        op.execute(sa.text("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'CONVOCATION_PARENT'"))


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'enum sans reconstruire
    # le type. Downgrade = no-op (comme 033/041/047).
    pass
