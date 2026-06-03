"""Convert position column from servantposition enum to VARCHAR to fix asyncpg DatatypeMismatchError

asyncpg (binary protocol) sends enum values with OID 25 (text). PostgreSQL binary
protocol does not perform implicit casts from text OID to custom enum OID, causing
DatatypeMismatchError on every INSERT that includes a position value (including NULL).
Converting to VARCHAR(64) lets asyncpg send the value as text and PostgreSQL stores it
directly, while the Python-level ServantPosition enum continues to enforce allowed values.

Revision ID: 038
Revises: 037
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "038"
down_revision: Union[str, None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert column type (USING casts existing enum values to text, NULL stays NULL)
    op.execute("ALTER TABLE users ALTER COLUMN position TYPE VARCHAR(64) USING position::text")
    # Drop the now-unused enum type
    op.execute("DROP TYPE IF EXISTS servantposition CASCADE")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE servantposition AS ENUM ("
        "'DELEGUE', 'VICE_DELEGUE', 'CENSEUR', 'CENSEUR_ADJOINT', "
        "'SECRETAIRE_GENERAL', 'SECRETAIRE_GENERAL_ADJOINT', 'ECONOME', "
        "'COMMISSAIRE_AUX_COMPTES', 'INTENDANT', 'CHARGE_LITURGIE', "
        "'CEREMONIARE', 'CHARGE_SPORTS_CULTURE', 'CHARGE_CLASSEMENT', "
        "'CONSEILLER', 'SERVANT_AUTEL')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN position TYPE servantposition USING position::servantposition"
    )
