"""Convert birth_date and baptism_date from timestamptz to VARCHAR for encrypted storage

Migration 022 documented that birth_date and baptism_date would store AES-256-GCM
base64url-encoded blobs (encrypted PII per Loi 2024/017). The entity was updated to
use SAString for these fields, but the DB columns were never migrated from the original
DateTime(timezone=True) type created in migration 020.

asyncpg binary protocol casts SAString parameters as VARCHAR ($n::VARCHAR), which
PostgreSQL rejects for timestamptz columns even for NULL values (DatatypeMismatchError).
Converting to VARCHAR(500) aligns the schema with the entity definition and allows
encrypted blob storage.

Revision ID: 039
Revises: 038
Create Date: 2026-06-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "039"
down_revision: Union[str, None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ALTER COLUMN birth_date TYPE VARCHAR(500) USING birth_date::text"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN baptism_date TYPE VARCHAR(500) USING baptism_date::text"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE users ALTER COLUMN birth_date TYPE TIMESTAMP WITH TIME ZONE "
        "USING birth_date::timestamp with time zone"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN baptism_date TYPE TIMESTAMP WITH TIME ZONE "
        "USING baptism_date::timestamp with time zone"
    )
