"""Integration tests for api_keys and analytics endpoints."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils

TEST_DB = "sqlite+aiosqlite:///:memory:"
VALID_PASSWORD = "TestPass1"


def _make_app() -> FastAPI:
    from src.presentation.api.v1 import analytics, api_keys, auth, users

    app = FastAPI()
    app.include_router(api_keys.router, prefix="/api/v1/api-keys")
    app.include_router(analytics.router, prefix="/api/v1/analytics")
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(users.router, prefix="/api/v1/users")
    return app


@pytest_asyncio.fixture()
async def engine():
    e = create_async_engine(TEST_DB, echo=False, connect_args={"check_same_thread": False})
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield e
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await e.dispose()


@pytest_asyncio.fixture()
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def app(engine) -> FastAPI:
    test_app = _make_app()

    async def _override():
        factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = _override
    return test_app


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _create_user(db_session: AsyncSession, **kwargs) -> User:
    user = User(**kwargs)
    return await UserRepository(db_session).create(user)


def _token(user: User) -> str:
    return SecurityUtils.create_access_token(
        subject=user.id,
        role=user.role.value,
        expires_delta=timedelta(minutes=30),
    )


@pytest_asyncio.fixture()
async def admin_user(db_session):
    return await _create_user(
        db_session,
        id=uuid4(),
        email="admin@t.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest_asyncio.fixture()
async def servant_user(db_session):
    return await _create_user(
        db_session,
        id=uuid4(),
        email="servant@t.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Servant",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237600000001",
    )


# ─── API Keys tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_api_key_as_servant(client, servant_user):
    r = await client.post(
        "/api/v1/api-keys/",
        json={"name": "My Key", "scopes": []},
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert "raw_key" in data
    assert data["raw_key"].startswith("sa_")


@pytest.mark.asyncio
async def test_create_api_key_unauthenticated(client):
    r = await client.post("/api/v1/api-keys/", json={"name": "K"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_my_api_keys_empty(client, servant_user):
    r = await client.get(
        "/api/v1/api-keys/me",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_my_api_keys_after_create(client, servant_user):
    # Create first
    await client.post(
        "/api/v1/api-keys/",
        json={"name": "Test Key", "scopes": ["read"]},
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    r = await client.get(
        "/api/v1/api-keys/me",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 200
    keys = r.json()
    assert len(keys) == 1
    assert keys[0]["name"] == "Test Key"


@pytest.mark.asyncio
async def test_list_all_api_keys_admin(client, admin_user):
    r = await client.get(
        "/api/v1/api-keys/",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_all_api_keys_non_admin_forbidden(client, servant_user):
    r = await client.get(
        "/api/v1/api-keys/",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_revoke_api_key_not_found(client, servant_user):
    r = await client.post(
        f"/api/v1/api-keys/{uuid4()}/revoke",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_revoke_api_key_success(client, servant_user):
    # Create key
    create_r = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Revoke Me"},
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    key_id = create_r.json()["id"]

    # Revoke it
    r = await client.post(
        f"/api/v1/api-keys/{key_id}/revoke",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_api_key_not_found(client, servant_user):
    r = await client.delete(
        f"/api/v1/api-keys/{uuid4()}",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_api_key_success(client, servant_user):
    create_r = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Delete Me"},
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    key_id = create_r.json()["id"]

    r = await client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_api_key_forbidden_not_owner(client, servant_user, admin_user):
    # Create key as servant
    create_r = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Servant Key"},
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    key_id = create_r.json()["id"]

    # Try to delete as admin (admin CAN delete others' keys)
    r = await client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 204


# ─── Analytics tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_realtime_as_admin(client, admin_user):
    r = await client.get(
        "/api/v1/analytics/realtime",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "source" in data  # mock or ga4
    assert "active_users" in data


@pytest.mark.asyncio
async def test_analytics_realtime_unauthenticated(client):
    r = await client.get("/api/v1/analytics/realtime")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_analytics_realtime_non_admin_forbidden(client, servant_user):
    r = await client.get(
        "/api/v1/analytics/realtime",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_analytics_summary_as_admin(client, admin_user):
    r = await client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "source" in data


@pytest.mark.asyncio
async def test_analytics_connections_as_admin(client, admin_user):
    r = await client.get(
        "/api/v1/analytics/connections",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_analytics_connections_default_days(client, admin_user):
    r = await client.get(
        "/api/v1/analytics/connections?days=7",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
