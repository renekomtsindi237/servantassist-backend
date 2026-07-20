"""Integration tests for dashboard and classement API endpoints."""

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


# ─── Test app including dashboard + classement ────────────────────────────────


def _make_app() -> FastAPI:
    from src.presentation.api.v1 import admin, auth, classement, dashboard, users

    app = FastAPI()
    app.include_router(dashboard.router, prefix="/api/v1/dashboard")
    app.include_router(classement.router, prefix="/api/v1/classement")
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(users.router, prefix="/api/v1/users")
    app.include_router(admin.router, prefix="/api/v1/admin")
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
async def aumonier_user(db_session):
    return await _create_user(
        db_session,
        id=uuid4(),
        email="aumonier@t.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Aumonier",
        last_name="Test",
        role=UserRole.AUMÔNIER,
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


# ─── Dashboard tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_summary_as_admin(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "total_servants" in data
    assert "attendance_rate_percent" in data
    assert "cotisation_rate_percent" in data


@pytest.mark.asyncio
async def test_dashboard_summary_as_servant(client, servant_user):
    r = await client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated(client):
    r = await client.get("/api/v1/dashboard/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_attendance_trend_admin(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/attendance",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "points" in data
    assert "average_rate_percent" in data


@pytest.mark.asyncio
async def test_dashboard_attendance_trend_weekly(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/attendance?group_by=week",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["period_label"] == "Tendance hebdomadaire"


@pytest.mark.asyncio
async def test_dashboard_attendance_invalid_group_by(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/attendance?group_by=invalid",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    # Falls back to monthly
    assert data["period_label"] == "Tendance mensuelle"


@pytest.mark.asyncio
async def test_dashboard_attendance_servant_forbidden(client, servant_user):
    r = await client.get(
        "/api/v1/dashboard/attendance",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_cotisations_admin(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/cotisations",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "period_name" in data
    assert data["total_members"] == 0


@pytest.mark.asyncio
async def test_dashboard_cotisations_aumonier(client, aumonier_user):
    r = await client.get(
        "/api/v1/dashboard/cotisations",
        headers={"Authorization": f"Bearer {_token(aumonier_user)}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_upcoming_events(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/events/upcoming",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_dashboard_top_servants_admin(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/top-servants",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_dashboard_top_servants_limit(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/top-servants?limit=3",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200


# ─── Classement tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classement_list_published_unauthenticated(client):
    r = await client.get("/api/v1/classement/published")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_classement_list_published_as_servant(client, servant_user):
    r = await client.get(
        "/api/v1/classement/published",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_classement_list_requires_role(client, servant_user):
    """Non-classement-manager servant → 403."""
    r = await client.get(
        "/api/v1/classement/",
        headers={"Authorization": f"Bearer {_token(servant_user)}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_classement_list_as_admin(client, admin_user):
    r = await client.get(
        "/api/v1/classement/",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "total" in data


@pytest.mark.asyncio
async def test_classement_get_not_found(client, admin_user):
    r = await client.get(
        f"/api/v1/classement/{uuid4()}",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_classement_create_as_admin(client, admin_user):
    payload = {
        "type": "DIMANCHE",
        "date": "2026-06-08",
        "heure": "08:00",
        "lieu": "Basilique",
        "postes": [],
    }
    r = await client.post(
        "/api/v1/classement/",
        json=payload,
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code in (200, 201)
    if r.status_code in (200, 201):
        data = r.json()
        assert "id" in data
        assert data["type"] == "DIMANCHE"


@pytest.mark.asyncio
async def test_classement_delete_not_found(client, admin_user):
    r = await client.delete(
        f"/api/v1/classement/{uuid4()}",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_classement_attendance_trend_with_dates(client, admin_user):
    r = await client.get(
        "/api/v1/dashboard/attendance?start_date=2026-01-01T00:00:00&end_date=2026-06-01T00:00:00",
        headers={"Authorization": f"Bearer {_token(admin_user)}"},
    )
    assert r.status_code == 200
