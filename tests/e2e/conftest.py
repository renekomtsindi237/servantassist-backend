"""
Fixtures spécifiques aux tests e2e.

Utilisent la vraie ``main.app`` (avec routes système /, /health, /ready, etc.)
et patchent le sessionmanager pour pointer sur SQLite en mémoire.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.database.session import get_db_session
from src.main import app as main_app

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def e2e_engine():
    engine = create_async_engine(
        _TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def main_client(e2e_engine):
    """
    Client ASGI pointant sur la vraie main.app avec SQLite en mémoire.

    Deux overrides nécessaires :
    1. ``get_db_session`` DI — utilisé par tous les routers.
    2. ``sessionmanager`` — utilisé directement par /health et /ready.
    """
    import src.infrastructure.database.session as session_mod

    # Fabrique de session partagée pour que /health et les routers
    # voient les mêmes tables.
    factory = async_sessionmaker(bind=e2e_engine, class_=AsyncSession, expire_on_commit=False)

    # 1. Override DI
    async def _override_session():
        async with factory() as session:
            yield session

    main_app.dependency_overrides[get_db_session] = _override_session

    # 2. Patch sessionmanager (utilisé par /health et /ready)
    old_engine = session_mod.sessionmanager._engine
    old_factory = session_mod.sessionmanager._sessionmaker
    session_mod.sessionmanager._engine = e2e_engine
    session_mod.sessionmanager._sessionmaker = factory

    try:
        async with AsyncClient(
            transport=ASGITransport(app=main_app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        main_app.dependency_overrides.pop(get_db_session, None)
        session_mod.sessionmanager._engine = old_engine
        session_mod.sessionmanager._sessionmaker = old_factory
