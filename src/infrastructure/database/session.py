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
      - for_migrations=False → session pooler (port 5432) via Supavisor
        Le pooler transaction (port 6543) est incompatible avec le protocole
        extended query d'asyncpg (DuplicatePreparedStatementError).
    """
    if settings.is_supabase_env:
        if for_migrations:
            url = settings.SUPABASE_DB_DIRECT_URL
            if not url:
                raise RuntimeError(f"APP_ENV={settings.APP_ENV} mais SUPABASE_DB_DIRECT_URL n'est pas configuré.")
        else:
            url = settings.SUPABASE_DB_POOLER_URL
            if not url:
                raise RuntimeError(f"APP_ENV={settings.APP_ENV} mais SUPABASE_DB_POOLER_URL n'est pas configuré.")
            # Supavisor session mode (port 5432) au lieu du mode transaction (port 6543).
            # Le mode session maintient une session PG persistante par connexion du pool,
            # ce qui est compatible avec les prepared statements d'asyncpg.
            url = url.replace(":6543/", ":5432/")
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

    Supabase session pooler (port 5432 / Supavisor) :
      - pool_size réduit : chaque slot du pool occupe une connexion PG réelle
        GUNICORN_WORKERS × pool_size ≤ quota Supabase (free ≈ 15, starter = 200)
    """
    import multiprocessing
    import os

    base: dict[str, Any] = {
        "echo": settings.APP_DEBUG,
        "pool_pre_ping": True,
    }

    if settings.is_supabase_env:
        workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count()))
        # Session pooler : chaque slot du pool occupe une connexion PG réelle.
        # Supabase free = ~15 connexions directes ; starter = 200 via pooler session.
        # Budget conservateur : 5 connexions par worker → 2 workers × 5 = 10 max.
        pool_size = max(2, min(5, 12 // workers))
        max_overflow = 2

        base.update(
            {
                "connect_args": {
                    # Timeout de connexion initiale (évite les attentes infinies)
                    "timeout": 10,
                    # Disable asyncpg prepared-statement cache.
                    # Supabase Supavisor (session mode, port 5432) reuses connections
                    # across requests. When a schema changes (e.g. enum → varchar),
                    # stale cached OIDs cause DatatypeMismatchError. Setting cache size
                    # to 0 forces fresh parameter-type negotiation on every query.
                    "statement_cache_size": 0,
                    # Statement timeout : tue toute requête qui dépasse 30s
                    "server_settings": {
                        "statement_timeout": "30000",  # ms
                        "idle_in_transaction_session_timeout": "60000",  # ms
                        "application_name": f"servantassist-{os.environ.get('APP_ENV', 'app')}",
                    },
                },
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": 15,  # Attente max pour obtenir une connexion du pool
                "pool_recycle": 1800,  # Recrée la connexion après 30 min
                "pool_pre_ping": True,  # Vérifie la connexion avant utilisation
            }
        )

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


try:
    sessionmanager = DatabaseSessionManager(
        get_db_url(for_migrations=False),
        _build_engine_kwargs(),
    )
except RuntimeError:
    # Migration context: only SUPABASE_DB_DIRECT_URL is set; SUPABASE_DB_POOLER_URL
    # is absent. Alembic env.py imports get_db_url() from this module but never
    # uses sessionmanager, so deferring creation here is safe.
    sessionmanager = None  # type: ignore[assignment]


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
