"""
Tests unitaires — AuthService (logique métier, repositories mockés).
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.auth_service import AuthService
from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.entities.user import User, UserRole
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.schemas.auth import UserCreate, UserLogin, UserPhoneLogin

VALID_PASSWORD = "TestPass1"
HASHED = SecurityUtils.get_password_hash(VALID_PASSWORD)


def _make_user(
    role: UserRole,
    email: str = "u@t.com",
    phone: str = "+237600000001",
    active: bool = True,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password=HASHED,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=active,
        phone_number=phone,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  AUTHENTICATE — EMAIL LOGIN
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAuthenticateEmail:
    """POST /auth/login — login par email."""

    async def test_admin_email_login_success(self):
        user = _make_user(UserRole.ADMIN, email="admin@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserLogin(email="admin@t.com", password=VALID_PASSWORD))
        assert result.email == "admin@t.com"
        assert result.role == UserRole.ADMIN

    async def test_aumonier_email_login_success(self):
        user = _make_user(UserRole.AUMÔNIER, email="aum@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserLogin(email="aum@t.com", password=VALID_PASSWORD))
        assert result.role == UserRole.AUMÔNIER

    async def test_servant_email_login_rejected_403(self):
        """Un SERVANT ne peut pas se connecter par email → 403."""
        user = _make_user(UserRole.SERVANT, email="srv@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="srv@t.com", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_parent_email_login_rejected_403(self):
        """Un PARENT ne peut pas se connecter par email → 403."""
        user = _make_user(UserRole.PARENT, email="par@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="par@t.com", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_nonexistent_email_401(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="nope@t.com", password="whatever"))
        assert exc_info.value.status_code == 401

    async def test_wrong_password_401(self):
        user = _make_user(UserRole.ADMIN, email="admin@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="admin@t.com", password="WrongPass1"))
        assert exc_info.value.status_code == 401

    async def test_inactive_user_403(self):
        user = _make_user(UserRole.ADMIN, email="admin@t.com", active=False)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="admin@t.com", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  AUTHENTICATE — PHONE LOGIN
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAuthenticatePhone:
    """POST /auth/login/phone — login par téléphone."""

    async def test_servant_phone_login_success(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserPhoneLogin(phone_number="+237600000001", password=VALID_PASSWORD))
        assert result.role == UserRole.SERVANT

    async def test_parent_phone_login_success(self):
        user = _make_user(UserRole.PARENT, phone="+237600000002")
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserPhoneLogin(phone_number="+237600000002", password=VALID_PASSWORD))
        assert result.role == UserRole.PARENT

    async def test_admin_phone_login_rejected_403(self):
        """Un ADMIN ne peut pas se connecter par téléphone → 403."""
        user = _make_user(UserRole.ADMIN, phone="+237600000003")
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237600000003", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_aumonier_phone_login_rejected_403(self):
        user = _make_user(UserRole.AUMÔNIER, phone="+237600000004")
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237600000004", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_nonexistent_phone_401(self):
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237699999999", password="x"))
        assert exc_info.value.status_code == 401

    async def test_wrong_password_phone_401(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237600000001", password="WrongPass1"))
        assert exc_info.value.status_code == 401

    async def test_inactive_phone_user_403(self):
        user = _make_user(UserRole.SERVANT, active=False)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237600000001", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  REGISTER — SERVANT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestRegisterServant:
    async def test_servant_self_register_success(self):
        created = _make_user(UserRole.SERVANT, email="new@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)
        service = AuthService(repo)

        result = await service.register_user(
            UserCreate(
                email="new@t.com",
                password=VALID_PASSWORD,
                first_name="A",
                last_name="B",
                phone_number="+237600000010",
                role=UserRole.SERVANT,
            )
        )
        assert result.role == UserRole.SERVANT

    async def test_duplicate_email_400(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=_make_user(UserRole.SERVANT))
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="u@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000010",
                    role=UserRole.SERVANT,
                )
            )
        assert exc_info.value.status_code == 400

    async def test_duplicate_phone_400(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=_make_user(UserRole.SERVANT))
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="new@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000001",
                    role=UserRole.SERVANT,
                )
            )
        assert exc_info.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  REGISTER — PARENT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestRegisterParent:
    async def test_parent_with_valid_invitation(self):
        created = _make_user(UserRole.PARENT, email="parent@t.com")
        invitation = MagicMock()
        invitation.email = None
        invitation.phone_number = None

        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)

        inv_repo = AsyncMock()
        inv_repo.get_by_code = AsyncMock(return_value=invitation)
        inv_repo.mark_as_used = AsyncMock()

        service = AuthService(repo, inv_repo)
        result = await service.register_user(
            UserCreate(
                email="parent@t.com",
                password=VALID_PASSWORD,
                first_name="A",
                last_name="B",
                phone_number="+237600000020",
                role=UserRole.PARENT,
            ),
            invitation_code="INV-VALID",
        )
        assert result.role == UserRole.PARENT
        inv_repo.mark_as_used.assert_called_once()

    async def test_parent_without_code_400(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)

        service = AuthService(repo, AsyncMock())
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="p@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000020",
                    role=UserRole.PARENT,
                ),
                invitation_code=None,
            )
        assert exc_info.value.status_code == 400

    async def test_parent_with_invalid_code_400(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)

        inv_repo = AsyncMock()
        inv_repo.get_by_code = AsyncMock(return_value=None)

        service = AuthService(repo, inv_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="p@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000020",
                    role=UserRole.PARENT,
                ),
                invitation_code="INV-INVALID",
            )
        assert exc_info.value.status_code == 400

    async def test_parent_email_locked_invitation_mismatch_403(self):
        invitation = MagicMock()
        invitation.email = "specific@t.com"
        invitation.phone_number = None

        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)

        inv_repo = AsyncMock()
        inv_repo.get_by_code = AsyncMock(return_value=invitation)

        service = AuthService(repo, inv_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="wrong@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000020",
                    role=UserRole.PARENT,
                ),
                invitation_code="INV-LOCKED",
            )
        assert exc_info.value.status_code == 403

    async def test_parent_phone_locked_invitation_mismatch_403(self):
        invitation = MagicMock()
        invitation.email = None
        invitation.phone_number = "+237699999999"

        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)

        inv_repo = AsyncMock()
        inv_repo.get_by_code = AsyncMock(return_value=invitation)

        service = AuthService(repo, inv_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="p@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    phone_number="+237600000020",
                    role=UserRole.PARENT,
                ),
                invitation_code="INV-PHONELOCKED",
            )
        assert exc_info.value.status_code == 403

    async def test_parent_created_by_admin_no_code_needed(self):
        """Un admin peut créer un PARENT sans code d'invitation."""
        created = _make_user(UserRole.PARENT, email="p@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)

        service = AuthService(repo)
        result = await service.register_user(
            UserCreate(
                email="p@t.com",
                password=VALID_PASSWORD,
                first_name="A",
                last_name="B",
                phone_number="+237600000020",
                role=UserRole.PARENT,
            ),
            invitation_code=None,
            admin_id=uuid4(),
        )
        assert result.role == UserRole.PARENT


# ═══════════════════════════════════════════════════════════════════════════
#  REGISTER — ADMIN / AUMÔNIER (restrictions)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestRegisterRestricted:
    async def test_admin_self_register_403(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="admin@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    role=UserRole.ADMIN,
                ),
                admin_id=None,
            )
        assert exc_info.value.status_code == 403

    async def test_aumonier_self_register_403(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                UserCreate(
                    email="aum@t.com",
                    password=VALID_PASSWORD,
                    first_name="A",
                    last_name="B",
                    role=UserRole.AUMÔNIER,
                ),
                admin_id=None,
            )
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  CREATE TOKENS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestCreateTokens:
    async def test_returns_token_with_bearer_type(self):
        user = _make_user(UserRole.ADMIN)
        repo = AsyncMock()
        service = AuthService(repo)

        token = await service.create_tokens(user)
        assert token.token_type == "bearer"
        assert token.access_token
        assert token.refresh_token

    async def test_access_token_contains_role(self):
        from jose import jwt as jose_jwt

        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        service = AuthService(repo)

        token = await service.create_tokens(user)
        payload = jose_jwt.decode(
            token.access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["role"] == "SERVANT"
        assert payload["sub"] == user.email

    async def test_refresh_token_contains_role_and_type(self):
        from jose import jwt as jose_jwt

        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        user = _make_user(UserRole.PARENT)
        repo = AsyncMock()
        service = AuthService(repo)

        token = await service.create_tokens(user)
        payload = jose_jwt.decode(
            token.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["role"] == "PARENT"
        assert payload["type"] == "refresh"
