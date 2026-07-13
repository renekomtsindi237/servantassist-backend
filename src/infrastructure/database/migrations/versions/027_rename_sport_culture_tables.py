"""rename sport culture tables to match entity model names

Revision ID: 027
Revises: 026
Create Date: 2026-05-23

Migration 009 created event_participations / event_results / event_teams
but the entity models define sport_culture_participations / sport_culture_results / sport_culture_teams.
"""
from typing import Union

from alembic import op

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("event_participations", "sport_culture_participations")
    op.rename_table("event_results", "sport_culture_results")
    op.rename_table("event_teams", "sport_culture_teams")


def downgrade() -> None:
    op.rename_table("sport_culture_participations", "event_participations")
    op.rename_table("sport_culture_results", "event_results")
    op.rename_table("sport_culture_teams", "event_teams")
