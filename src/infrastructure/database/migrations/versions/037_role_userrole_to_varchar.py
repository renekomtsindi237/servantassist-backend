"""Convert role column from userrole enum to VARCHAR to fix asyncpg DatatypeMismatchError

asyncpg (binary protocol) sends enum values with OID 25 (text). PostgreSQL binary
protocol does not perform implicit casts from text OID to custom enum OID, causing
DatatypeMismatchError on every INSERT. Converting to VARCHAR(20) lets asyncpg send
the value as text and PostgreSQL stores it directly, while Python-level UserRole enum
continues to enforce the allowed values.

Revision ID: 037
Revises: 036
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "037"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert role column from userrole enum → VARCHAR(20)
    # USING role::text casts existing enum values to their string representation
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20) USING role::text")
    # Drop the now-unused PostgreSQL enum type
    op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    # Recreate the userrole enum and convert back
    op.execute(
        "CREATE TYPE userrole AS ENUM ('ADMIN', 'SERVANT', 'PARENT', 'AUMÔNIER')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole"
    )
