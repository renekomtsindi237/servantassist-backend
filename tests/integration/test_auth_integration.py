"""
Tests d'intégration — flux d'authentification complet (HTTP).

Schéma : SQLite en mémoire + FastAPI ASGI test client.

Particularité : les users DOIVENT être créés via UserRepository.create()
pour que le champ email_hmac soit renseigné (get_by_email utilise HMAC lookup).
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import VALID_PASSWORD

# ── Helper ───────────────────────────────────────────────────────────────


async def _create_servant(db_session: AsyncSession, email: str = "servant_auth@test.com") -> User:
    """Crée un servant en passant par le repository (email_hmac renseigné)."""
    repo = UserRepository(db_session)
    user = User(
        id=uuid4(),
        email=email,
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Auth",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237691000001",
    )
    return await repo.create(user)


async def _create_admin(db_session: AsyncSession) -> User:
    repo = UserRepository(db_session)
    user = User(
        id=uuid4(),
        email="admin_auth@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="AdminAuth",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    return await repo.create(user)


# ═══════════════════════════════════════════════════════════════════════════
#  Login par email (OAuth2 form data)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestEmailLogin:
    async def test_login_success_returns_tokens(self, client: AsyncClient, db_session: AsyncSession):
        await _create_admin(db_session)
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin_auth@test.com", "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client: AsyncClient, db_session: AsyncSession):
        await _create_admin(db_session)
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin_auth@test.com", "password": "WrongPass1!"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": VALID_PASSWORD},
        )
        assert response.status_code == 401

    async def test_servant_cannot_login_via_email_form(self, client: AsyncClient, db_session: AsyncSession):
        """
        SERVANT et PARENT ne doivent pas pouvoir se connecter via /login (réservé ADMIN/AUMÔNIER).
        Ils utilisent /login/phone.
        """
        await _create_servant(db_session)
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "servant_auth@test.com", "password": VALID_PASSWORD},
        )
        # Le service refuse les rôles qui ne peuvent pas utiliser l'email login
        assert response.status_code in (401, 403)

    async def test_login_inactive_user_returns_4xx(self, client: AsyncClient, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = User(
            id=uuid4(),
            email="inactive_auth@test.com",
            hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
            first_name="Inactive",
            last_name="Auth",
            role=UserRole.ADMIN,
            is_active=False,
        )
        await repo.create(user)
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "inactive_auth@test.com", "password": VALID_PASSWORD},
        )
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
#  Login par téléphone
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPhoneLogin:
    async def test_phone_login_servant_success(self, client: AsyncClient, db_session: AsyncSession):
        await _create_servant(db_session)
        response = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237691000001", "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_phone_login_wrong_password(self, client: AsyncClient, db_session: AsyncSession):
        await _create_servant(db_session)
        response = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237691000001", "password": "WrongPass1!"},
        )
        assert response.status_code == 401

    async def test_phone_login_unknown_number(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237000000000", "password": VALID_PASSWORD},
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  Inscription (SERVANT — sans invitation)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestRegister:
    async def test_register_servant_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newservant@test.com",
                "password": "NewPass1!",
                "first_name": "Nouveau",
                "last_name": "Servant",
                "role": "SERVANT",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "newservant@test.com"
        assert body["role"] == "SERVANT"
        assert "hashed_password" not in body

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {
            "email": "duplicate@test.com",
            "password": "NewPass1!",
            "first_name": "A",
            "last_name": "B",
            "role": "SERVANT",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code in (400, 409)

    async def test_register_admin_forbidden(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "adminreg@test.com",
                "password": "NewPass1!",
                "first_name": "A",
                "last_name": "B",
                "role": "ADMIN",
            },
        )
        assert response.status_code == 403

    async def test_register_weak_password_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@test.com",
                "password": "weak",
                "first_name": "A",
                "last_name": "B",
                "role": "SERVANT",
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  Refresh token
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestRefreshToken:
    async def test_refresh_returns_new_tokens(self, client: AsyncClient, db_session: AsyncSession):
        await _create_admin(db_session)
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin_auth@test.com", "password": VALID_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body

    async def test_refresh_invalid_token_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert response.status_code == 401

    async def test_access_token_cannot_be_used_as_refresh(self, client: AsyncClient, db_session: AsyncSession):
        await _create_admin(db_session)
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin_auth@test.com", "password": VALID_PASSWORD},
        )
        access_token = login.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},  # mauvais type de token
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  Logout
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestLogout:
    async def test_logout_success(self, client: AsyncClient, db_session: AsyncSession):
        await _create_servant(db_session)
        login = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237691000001", "password": VALID_PASSWORD},
        )
        access_token = login.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    async def test_logout_without_token_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    async def test_logout_with_bad_token_returns_400_or_401(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert response.status_code in (400, 401)
