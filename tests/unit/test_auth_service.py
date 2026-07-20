"""
Tests unitaires â€" AuthService (logique mÃ©tier, repositories mockÃ©s).
"""

from datetime import timedelta
from typing import Optional
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
    email: Optional[str] = "u@t.com",
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  AUTHENTICATE â€" EMAIL LOGIN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@pytest.mark.unit
class TestAuthenticateEmail:
    """POST /auth/login â€" login par email."""

    async def test_admin_email_login_success(self):
        user = _make_user(UserRole.ADMIN, email="admin@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserLogin(email="admin@t.com", password=VALID_PASSWORD))
        assert result.email == "admin@t.com"
        assert result.role == UserRole.ADMIN

    async def test_AUMÔNIER_email_login_success(self):
        user = _make_user(UserRole.AUMÔNIER, email="aum@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        result = await service.authenticate_user(UserLogin(email="aum@t.com", password=VALID_PASSWORD))
        assert result.role == UserRole.AUMÔNIER

    async def test_servant_email_login_rejected_403(self):
        """Un SERVANT ne peut pas se connecter par email â†’ 403."""
        user = _make_user(UserRole.SERVANT, email="srv@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserLogin(email="srv@t.com", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_parent_email_login_rejected_403(self):
        """Un PARENT ne peut pas se connecter par email â†’ 403."""
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


# ═══════════════════════════════════════════════════════════════════════
#  AUTHENTICATE — OAUTH (Google, connexion uniquement)
# ═══════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAuthenticateOAuth:
    """POST /auth/oauth/{provider} — connexion via jeton Google vérifié."""

    def _identity(self, email="oauth@t.com", verified=True, subject="sub-123"):
        from src.infrastructure.services.oauth_verifier import OAuthIdentity

        return OAuthIdentity(email=email, email_verified=verified, subject=subject)

    async def test_google_login_success_existing_user(self):
        user = _make_user(UserRole.AUMÔNIER, email="oauth@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        repo.update = AsyncMock(return_value=user)
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=self._identity(),
        ):
            result = await service.authenticate_oauth("google", "fake-token")

        assert result.email == "oauth@t.com"
        repo.update.assert_awaited_once()

    async def test_already_linked_does_not_call_update(self):
        user = _make_user(UserRole.AUMÔNIER, email="oauth@t.com")
        user.oauth_provider = "google"
        user.oauth_subject = "sub-123"
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        repo.update = AsyncMock(return_value=user)
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=self._identity(subject="sub-123"),
        ):
            await service.authenticate_oauth("google", "fake-token")

        repo.update.assert_not_awaited()

    async def test_unverified_email_401(self):
        repo = AsyncMock()
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=self._identity(verified=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.authenticate_oauth("google", "fake-token")
        assert exc_info.value.status_code == 401
        repo.get_by_email.assert_not_awaited()

    async def test_no_matching_account_404(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=self._identity(),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.authenticate_oauth("google", "fake-token")
        assert exc_info.value.status_code == 404

    async def test_inactive_account_403(self):
        user = _make_user(UserRole.AUMÔNIER, email="oauth@t.com", active=False)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=self._identity(),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.authenticate_oauth("google", "fake-token")
        assert exc_info.value.status_code == 403

    async def test_invalid_token_401(self):
        from src.infrastructure.services.oauth_verifier import OAuthVerificationError

        repo = AsyncMock()
        service = AuthService(repo)

        with patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            side_effect=OAuthVerificationError("bad signature"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.authenticate_oauth("google", "fake-token")
        assert exc_info.value.status_code == 401
        repo.get_by_email.assert_not_awaited()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  AUTHENTICATE â€" PHONE LOGIN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@pytest.mark.unit
class TestAuthenticatePhone:
    """POST /auth/login/phone â€" login par tÃ©lÃ©phone."""

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
        """Un ADMIN ne peut pas se connecter par tÃ©lÃ©phone â†’ 403."""
        user = _make_user(UserRole.ADMIN, phone="+237600000003")
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(UserPhoneLogin(phone_number="+237600000003", password=VALID_PASSWORD))
        assert exc_info.value.status_code == 403

    async def test_AUMÔNIER_phone_login_rejected_403(self):
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  REGISTER â€" SERVANT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  REGISTER â€" PARENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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
        """Un admin peut crÃ©er un PARENT sans code d'invitation."""
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  REGISTER â€" ADMIN / AUMÔNIER (restrictions)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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

    async def test_AUMÔNIER_self_register_403(self):
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  CREATE TOKENS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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
        import jwt as jose_jwt

        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        # SERVANT triggers a NominationRepository lookup (position claim
        # sourced from Nomination) — mock an empty result explicitly rather
        # than relying on AsyncMock's default recursive child behavior.
        exec_result = MagicMock()
        exec_result.all = MagicMock(return_value=[])
        repo.session = MagicMock()
        repo.session.exec = AsyncMock(return_value=exec_result)
        service = AuthService(repo)

        token = await service.create_tokens(user)
        payload = jose_jwt.decode(
            token.access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["role"] == "SERVANT"
        assert payload["sub"] == str(user.id)

    async def test_refresh_token_contains_role_and_type(self):
        import jwt as jose_jwt

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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  FORGOT_PASSWORD / RESET_PASSWORD / OTP FLOWS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@pytest.mark.unit
class TestForgotAndReset:

    async def test_forgot_password_unknown_email_silent(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)
        email_svc = AsyncMock()
        await service.forgot_password("nobody@t.com", email_svc)
        email_svc.send_reset_password_email.assert_not_called()

    async def test_forgot_password_inactive_user_silent(self):
        user = _make_user(UserRole.SERVANT, active=False)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)
        email_svc = AsyncMock()
        await service.forgot_password(user.email, email_svc)
        email_svc.send_reset_password_email.assert_not_called()

    async def test_forgot_password_sends_email(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)
        email_svc = AsyncMock()
        email_svc.send_reset_password_email = AsyncMock()
        await service.forgot_password(user.email, email_svc)
        email_svc.send_reset_password_email.assert_called_once()

    async def test_request_reset_code_unknown_email_silent(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        service = AuthService(repo)
        code_repo = AsyncMock()
        email_svc = AsyncMock()
        await service.request_reset_code("nobody@t.com", code_repo, email_svc)
        code_repo.create.assert_not_called()

    async def test_request_reset_code_success(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)
        code_repo = AsyncMock()
        email_svc = AsyncMock()
        email_svc.send_reset_code_email = AsyncMock()
        await service.request_reset_code(user.email, code_repo, email_svc)
        code_repo.create.assert_called_once()
        email_svc.send_reset_code_email.assert_called_once()

    async def test_verify_reset_code_invalid(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()
        code_repo.get_valid = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_reset_code("u@t.com", "000000", code_repo)
        assert exc_info.value.status_code == 400

    async def test_verify_reset_code_success(self):
        from uuid import uuid4 as _uuid4

        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=user)
        service = AuthService(repo)
        entry = MagicMock()
        entry.id = _uuid4()
        code_repo = AsyncMock()
        code_repo.get_valid = AsyncMock(return_value=entry)
        code_repo.mark_used = AsyncMock()
        result = await service.verify_reset_code(user.email, "123456", code_repo)
        assert isinstance(result, str) and len(result) > 0
        code_repo.mark_used.assert_called_once_with(entry.id)

    async def test_request_reset_code_phone_not_found_silent(self):
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)
        code_repo = AsyncMock()
        await service.request_reset_code_phone("+237699000001", code_repo)
        code_repo.create.assert_not_called()

    async def test_request_reset_code_phone_success(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)
        code_repo = AsyncMock()
        await service.request_reset_code_phone(user.phone_number, code_repo)
        code_repo.create.assert_called_once()

    async def test_request_reset_code_phone_sends_via_whatsapp(self):
        """Le code doit réellement être envoyé (plus seulement loggé — ancien TODO corrigé)."""
        user = _make_user(UserRole.SERVANT, phone="+237699000002")
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)
        code_repo = AsyncMock()

        with patch(
            "src.infrastructure.services.whatsapp_service.WhatsAppService.send_otp_code",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await service.request_reset_code_phone(user.phone_number, code_repo)

        mock_send.assert_awaited_once()
        sent_phone, sent_code = mock_send.call_args.args
        assert sent_phone == "+237699000002"
        assert len(sent_code) == 6 and sent_code.isdigit()

    async def test_request_reset_code_phone_whatsapp_failure_is_silent(self):
        """Un échec d'envoi WhatsApp (Twilio down/non configuré) ne doit jamais remonter au client."""
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)
        code_repo = AsyncMock()

        with patch(
            "src.infrastructure.services.whatsapp_service.WhatsAppService.send_otp_code",
            new_callable=AsyncMock,
            side_effect=Exception("Twilio down"),
        ):
            await service.request_reset_code_phone(user.phone_number, code_repo)  # ne doit pas lever

        code_repo.create.assert_called_once()

    async def test_verify_reset_code_phone_user_not_found(self):
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)
        code_repo = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_reset_code_phone("+237699000001", "123456", code_repo)
        assert exc_info.value.status_code == 400

    async def test_verify_reset_code_phone_invalid_code(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)
        code_repo = AsyncMock()
        code_repo.get_valid = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_reset_code_phone(user.phone_number, "000000", code_repo)
        assert exc_info.value.status_code == 400

    async def test_verify_reset_code_phone_success(self):
        from uuid import uuid4 as _uuid4

        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get_by_phone = AsyncMock(return_value=user)
        service = AuthService(repo)
        entry = MagicMock()
        entry.id = _uuid4()
        code_repo = AsyncMock()
        code_repo.get_valid = AsyncMock(return_value=entry)
        code_repo.mark_used = AsyncMock()
        result = await service.verify_reset_code_phone(user.phone_number, "654321", code_repo)
        assert isinstance(result, str) and len(result) > 0


# ═══════════════════════════════════════════════════════════════════════
#  VÉRIFICATION DU TÉLÉPHONE À L'INSCRIPTION (aucun compte n'existe encore)
# ═══════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestPhoneVerification:
    async def test_send_phone_verification_code_creates_entry_and_sends(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()

        with patch(
            "src.infrastructure.services.whatsapp_service.WhatsAppService.send_otp_code",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await service.send_phone_verification_code("+237611110001", code_repo)

        code_repo.create.assert_called_once()
        mock_send.assert_awaited_once()
        sent_phone, sent_code = mock_send.call_args.args
        assert sent_phone == "+237611110001"
        assert len(sent_code) == 6 and sent_code.isdigit()

    async def test_send_phone_verification_code_whatsapp_failure_is_silent(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()

        with patch(
            "src.infrastructure.services.whatsapp_service.WhatsAppService.send_otp_code",
            new_callable=AsyncMock,
            side_effect=Exception("Twilio down"),
        ):
            await service.send_phone_verification_code("+237611110002", code_repo)  # ne doit pas lever

        code_repo.create.assert_called_once()

    async def test_send_phone_verification_code_rate_limited_after_5_sends(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()
        phone = "+237611110003"

        with patch(
            "src.infrastructure.services.whatsapp_service.WhatsAppService.send_otp_code",
            new_callable=AsyncMock,
            return_value=True,
        ):
            for _ in range(5):
                await service.send_phone_verification_code(phone, code_repo)
            with pytest.raises(HTTPException) as exc_info:
                await service.send_phone_verification_code(phone, code_repo)
        assert exc_info.value.status_code == 429

    async def test_verify_phone_code_invalid_code_400(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()
        code_repo.get_valid_by_phone_hmac = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.verify_phone_code("+237611110004", "000000", code_repo)
        assert exc_info.value.status_code == 400

    async def test_verify_phone_code_success_returns_token(self):
        from uuid import uuid4 as _uuid4

        repo = AsyncMock()
        service = AuthService(repo)
        entry = MagicMock()
        entry.id = _uuid4()
        code_repo = AsyncMock()
        code_repo.get_valid_by_phone_hmac = AsyncMock(return_value=entry)
        code_repo.mark_verified = AsyncMock()

        token = await service.verify_phone_code("+237611110005", "123456", code_repo)

        assert isinstance(token, str) and len(token) > 0
        code_repo.mark_verified.assert_awaited_once_with(entry.id, token)

    async def test_verify_phone_code_rate_limited_after_5_failures(self):
        repo = AsyncMock()
        service = AuthService(repo)
        code_repo = AsyncMock()
        code_repo.get_valid_by_phone_hmac = AsyncMock(return_value=None)
        phone = "+237611110006"

        for _ in range(5):
            with pytest.raises(HTTPException):
                await service.verify_phone_code(phone, "000000", code_repo)
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_phone_code(phone, "000000", code_repo)
        assert exc_info.value.status_code == 429


class TestRegisterPhoneVerification:
    """register_user(require_phone_verification=True) — inscription publique uniquement."""

    async def test_register_requires_verification_token_when_flag_set(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)

        data = UserCreate(
            email="v@t.com",
            password=VALID_PASSWORD,
            first_name="V",
            last_name="T",
            phone_number="+237622220001",
            role=UserRole.SERVANT,
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(data, require_phone_verification=True)
        assert exc_info.value.status_code == 400

    async def test_register_rejects_invalid_or_unknown_token(self):
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)
        phone_repo = AsyncMock()
        phone_repo.get_by_token = AsyncMock(return_value=None)

        data = UserCreate(
            email="v2@t.com",
            password=VALID_PASSWORD,
            first_name="V",
            last_name="T",
            phone_number="+237622220002",
            role=UserRole.SERVANT,
        )
        data = data.model_copy(update={"phone_verification_token": "bad-token"})
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(
                data,
                require_phone_verification=True,
                phone_verification_repository=phone_repo,
            )
        assert exc_info.value.status_code == 400

    async def test_register_succeeds_with_valid_token(self):
        created = _make_user(UserRole.SERVANT, email="v3@t.com")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)
        service = AuthService(repo)
        phone_repo = AsyncMock()
        phone_repo.get_by_token = AsyncMock(return_value=MagicMock())  # entrée vérifiée trouvée

        data = UserCreate(
            email="v3@t.com",
            password=VALID_PASSWORD,
            first_name="V",
            last_name="T",
            phone_number="+237622220003",
            role=UserRole.SERVANT,
        )
        data = data.model_copy(update={"phone_verification_token": "good-token"})
        result = await service.register_user(
            data,
            require_phone_verification=True,
            phone_verification_repository=phone_repo,
        )
        assert result is not None
        phone_repo.get_by_token.assert_awaited_once()

    async def test_register_parent_children_flow_unaffected(self):
        """POST /parent/children (skip_age_check=True) ne passe jamais
        require_phone_verification — doit continuer à fonctionner sans token."""
        created = _make_user(UserRole.SERVANT, email="child@bmra.servant.local")
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)
        service = AuthService(repo)

        data = UserCreate.model_construct(
            email=None,
            password=VALID_PASSWORD,
            first_name="Enfant",
            last_name="Test",
            role=UserRole.SERVANT,
            phone_number=None,
            birth_date=None,
        )
        result = await service.register_user(data, invitation_code=None, admin_id=None, skip_age_check=True)
        assert result is not None

    async def test_register_servant_no_email_stays_null(self):
        """SERVANT sans email → email reste None en base (plus d'auto-génération)."""
        created = _make_user(UserRole.SERVANT, email=None)
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created)
        service = AuthService(repo)

        result = await service.register_user(
            UserCreate(
                email=None,
                password=VALID_PASSWORD,
                first_name="A",
                last_name="B",
                phone_number="+237600000099",
                role=UserRole.SERVANT,
            )
        )
        assert result is not None
        call_arg = repo.create.call_args[0][0]
        assert call_arg.email is None
        repo.get_by_email.assert_not_awaited()  # aucune vérification d'unicité sur None

    async def test_register_servant_age_under_13_rejected(self):
        """Servant < 13 ans sans parent_id â†’ 422."""
        from datetime import date as _date
        from datetime import datetime as _dt

        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)
        service = AuthService(repo)

        birth = _dt(2020, 1, 1)
        data = UserCreate(
            email="young@t.com",
            password=VALID_PASSWORD,
            first_name="Y",
            last_name="O",
            phone_number="+237600000088",
            role=UserRole.SERVANT,
        )
        data = data.model_copy(update={"birth_date": birth})
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(data)
        assert exc_info.value.status_code == 422

    async def test_register_parent_invitation_phone_mismatch(self):
        """Invitation liÃ©e Ã  un tÃ©lÃ©phone, numÃ©ro diffÃ©rent â†’ 403."""
        repo = AsyncMock()
        repo.get_by_email = AsyncMock(return_value=None)
        repo.get_by_phone = AsyncMock(return_value=None)  # phone unique OK
        invitation = MagicMock()
        invitation.email = None
        invitation.phone_number = "+237699000001"
        inv_repo = AsyncMock()
        inv_repo.get_by_code = AsyncMock(return_value=invitation)
        service = AuthService(repo, inv_repo)

        data = UserCreate(
            email="p@t.com",
            password=VALID_PASSWORD,
            first_name="P",
            last_name="A",
            phone_number="+237699000002",
            role=UserRole.PARENT,
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.register_user(data, invitation_code="CODE")
        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestRefreshAndResetPassword:

    async def test_refresh_token_invalid_token(self):
        repo = AsyncMock()
        service = AuthService(repo)
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token("not.a.valid.token")
        assert exc.value.status_code == 401

    async def test_refresh_token_wrong_type(self):
        from src.infrastructure.config.settings import get_settings

        get_settings()
        user = _make_user(UserRole.ADMIN)
        repo = AsyncMock()
        service = AuthService(repo)
        # Create an access token (type='access', not 'refresh')
        access = await service.create_tokens(user)
        with pytest.raises(HTTPException) as exc:
            await service.refresh_token(access.access_token)
        assert exc.value.status_code == 401

    async def test_refresh_token_success(self):
        user = _make_user(UserRole.ADMIN)
        repo = AsyncMock()
        repo.get = AsyncMock(return_value=user)
        service = AuthService(repo)

        # Get real refresh token
        tokens = await service.create_tokens(user)

        with patch("src.infrastructure.security.token_blacklist.token_blacklist") as mock_bl:
            mock_bl.is_revoked = AsyncMock(return_value=False)
            mock_bl.revoke = AsyncMock()
            new_tokens = await service.refresh_token(tokens.refresh_token)

        assert new_tokens.access_token != tokens.access_token

    async def test_reset_password_invalid_token(self):
        repo = AsyncMock()
        service = AuthService(repo)
        with pytest.raises(HTTPException) as exc:
            await service.reset_password("not.a.valid.token", "NewPass123")
        assert exc.value.status_code == 400

    async def test_reset_password_success(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get = AsyncMock(return_value=user)
        repo.update = AsyncMock(return_value=user)
        service = AuthService(repo)

        reset_tok = SecurityUtils.create_reset_token(user.id)

        with patch("src.infrastructure.security.token_blacklist.token_blacklist") as mock_bl:
            mock_bl.is_revoked = AsyncMock(return_value=False)
            mock_bl.revoke = AsyncMock()
            await service.reset_password(reset_tok, "NewPass123")

        repo.update.assert_called_once()

    async def test_reset_password_with_email_service(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        repo.get = AsyncMock(return_value=user)
        repo.update = AsyncMock(return_value=user)
        service = AuthService(repo)

        reset_tok = SecurityUtils.create_reset_token(user.id)
        email_svc = AsyncMock()
        email_svc.send_password_changed_email = AsyncMock()

        with patch("src.infrastructure.security.token_blacklist.token_blacklist") as mock_bl:
            mock_bl.is_revoked = AsyncMock(return_value=False)
            mock_bl.revoke = AsyncMock()
            await service.reset_password(reset_tok, "NewPass123", email_service=email_svc)

        email_svc.send_password_changed_email.assert_called_once()

    async def test_reset_password_revoked_token(self):
        user = _make_user(UserRole.SERVANT)
        repo = AsyncMock()
        service = AuthService(repo)

        reset_tok = SecurityUtils.create_reset_token(user.id)

        with patch("src.infrastructure.security.token_blacklist.token_blacklist") as mock_bl:
            mock_bl.is_revoked = AsyncMock(return_value=True)
            with pytest.raises(HTTPException) as exc:
                await service.reset_password(reset_tok, "NewPass123")
        assert exc.value.status_code == 400
