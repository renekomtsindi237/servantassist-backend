import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context
from src.core.entities import *  # Import all entities to register them with SQLModel metadata
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import get_db_url

# Alembic Config object — accès aux valeurs de alembic.ini
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_migration_url() -> str:
    """
    URL de connexion pour les migrations Alembic.

    IMPORTANT — Supabase :
      Les migrations DOIVENT utiliser la connexion directe (port 5432),
      PAS le pgbouncer transaction pooler (port 6543).
      Raison : Alembic émet des SET/RESET et des DDL transactionnels qui
      nécessitent un mode « session » complet, incompatible avec le mode
      transaction de pgbouncer.

    development → URL locale identique au runtime.
    staging/production → SUPABASE_DB_DIRECT_URL (connexion directe).
    """
    return get_db_url(for_migrations=True)


def run_migrations_offline() -> None:
    """Mode offline : émet les SQL sans connexion réelle."""
    url = get_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Mode online : crée un moteur async et exécute les migrations.
    NullPool est obligatoire pour Alembic (pas de pool persistant).
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_migration_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
