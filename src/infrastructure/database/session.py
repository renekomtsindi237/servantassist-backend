from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.config.settings import get_settings

settings = get_settings()


def get_db_url(for_migrations: bool = False) -> str:
    """
    Retourne l'URL de connexion PostgreSQL adaptée à l'environnement.

    development → PostgreSQL local (via DATABASE_URL ou variables POSTGRES_*)
    staging / production → Supabase
      - for_migrations=True  → connexion directe (DDL, Alembic)
      - for_migrations=False → transaction pooler pgbouncer (runtime)
    """
    if settings.is_supabase_env:
        url = settings.SUPABASE_DB_DIRECT_URL if for_migrations else settings.SUPABASE_DB_POOLER_URL
        if not url:
            raise RuntimeError(
                f"APP_ENV={settings.APP_ENV} mais "
                f"{'SUPABASE_DB_DIRECT_URL' if for_migrations else 'SUPABASE_DB_POOLER_URL'} "
                "n'est pas configuré."
            )
        return _ensure_asyncpg(url)

    # ── Développement : PostgreSQL local ──────────────────────────────
    if settings.DATABASE_URL:
        return _ensure_asyncpg(settings.DATABASE_URL)
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def _ensure_asyncpg(url: str) -> str:
    """Convertit postgresql:// → postgresql+asyncpg:// si nécessaire."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _build_engine_kwargs() -> dict[str, Any]:
    """
    Options SQLAlchemy adaptées à l'environnement.

    Supabase pgbouncer (mode Transaction) impose :
      - prepared_statement_cache_size=0  → désactive les prepared statements
        (pgbouncer transaction mode ne les supporte pas entre connexions)
      - pool_size calibré par worker pour ne pas saturer pgbouncer :
        GUNICORN_WORKERS × pool_size ≤ quota Supabase (60 free / 200 pro)
    """
    import multiprocessing
    import os

    base: dict[str, Any] = {
        "echo": settings.APP_DEBUG,
        "pool_pre_ping": True,
    }

    if settings.is_supabase_env:
        workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count()))
        # Budget : 50 connexions pgbouncer réparties sur tous les workers
        pool_size = max(2, 50 // workers)
        max_overflow = pool_size

        base.update({
            "connect_args": {
                # Pgbouncer transaction mode — désactive prepared statements
                "prepared_statement_cache_size": 0,
                # Timeout de connexion initiale (évite les attentes infinies)
                "timeout": 10,
                # Statement timeout : tue toute requête qui dépasse 30s
                "server_settings": {
                    "statement_timeout": "30000",        # ms
                    "idle_in_transaction_session_timeout": "60000",  # ms
                    "application_name": f"servantassist-{os.environ.get('APP_ENV', 'app')}",
                },
            },
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": 15,       # Attente max pour obtenir une connexion du pool
            "pool_recycle": 1800,     # Recrée la connexion après 30 min
            "pool_pre_ping": True,    # Vérifie la connexion avant utilisation
        })

    return base


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(
            autocommit=False,
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self):
        if self._engine is None:
            raise RuntimeError("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncSession, None]:
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseSessionManager is not initialized")
        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._sessionmaker is None:
            raise RuntimeError("DatabaseSessionManager is not initialized")
        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(
    get_db_url(for_migrations=False),
    _build_engine_kwargs(),
)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
