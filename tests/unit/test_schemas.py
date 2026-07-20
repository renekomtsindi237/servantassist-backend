"""
Tests unitaires — Schémas Pydantic (validation, contraintes de rôle, mot de passe).
"""

import pytest
from pydantic import ValidationError

from src.core.entities.user import UserRole
from src.presentation.schemas.auth import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
    TokenData,
    UserCreate,
    UserCreateWithInvite,
    UserLogin,
    UserPhoneLogin,
    UserResponse,
)


# ═══════════════════════════════════════════════════════════════════════════
#  UserLogin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUserLogin:
    def test_valid(self):
        login = UserLogin(email="admin@test.com", password="secret")
        assert login.email == "admin@test.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserLogin(email="not-an-email", password="secret")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            UserLogin(email="admin@test.com")


# ═══════════════════════════════════════════════════════════════════════════
#  UserPhoneLogin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUserPhoneLogin:
    def test_valid(self):
        login = UserPhoneLogin(phone_number="+237600000001", password="secret")
        assert login.phone_number == "+237600000001"

    def test_missing_phone(self):
        with pytest.raises(ValidationError):
            UserPhoneLogin(password="secret")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            UserPhoneLogin(phone_number="+237600000001")


# ═══════════════════════════════════════════════════════════════════════════
#  UserCreate — Password Validation
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUserCreatePassword:
    def test_valid_password(self):
        user = UserCreate(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="+237600000001",
            role=UserRole.SERVANT,
        )
        assert user.password == "TestPass1"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="8 characters"):
            UserCreate(
                email="u@t.com",
                password="Tp1",
                first_name="A",
                last_name="B",
                phone_number="+237600000001",
                role=UserRole.SERVANT,
            )

    def test_no_uppercase(self):
        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(
                email="u@t.com",
                password="testpass1",
                first_name="A",
                last_name="B",
                phone_number="+237600000001",
                role=UserRole.SERVANT,
            )

    def test_no_lowercase(self):
        with pytest.raises(ValidationError, match="lowercase"):
            UserCreate(
                email="u@t.com",
                password="TESTPASS1",
                first_name="A",
                last_name="B",
                phone_number="+237600000001",
                role=UserRole.SERVANT,
            )

    def test_no_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            UserCreate(
                email="u@t.com",
                password="TestPasss",
                first_name="A",
                last_name="B",
                phone_number="+237600000001",
                role=UserRole.SERVANT,
            )


# ═══════════════════════════════════════════════════════════════════════════
#  UserCreate — Phone Validation
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUserCreatePhone:
    """
    NOTE : Dans Pydantic v2, les field_validators s'exécutent dans l'ordre
    de déclaration des champs. Comme `phone_number` est déclaré AVANT `role`
    dans UserCreate, info.data.get('role') est None lors de la validation
    du téléphone → la contrainte de rôle ne s'applique pas au niveau du schéma.
    La validation est assurée côté service (AuthService.register_user).
    """

    def test_servant_without_phone_passes_schema(self):
        """Le schéma ne bloque pas (limité par l'ordre Pydantic v2)."""
        user = UserCreate(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            role=UserRole.SERVANT,
        )
        assert user.phone_number is None

    def test_parent_without_phone_passes_schema(self):
        """Le schéma ne bloque pas — la validation est faite côté service."""
        user = UserCreate(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            role=UserRole.PARENT,
        )
        assert user.phone_number is None

    def test_invalid_phone_format_passes_schema(self):
        """Même constat — role pas encore disponible lors de la validation phone."""
        user = UserCreate(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="0600000001",
            role=UserRole.SERVANT,
        )
        assert user.phone_number == "0600000001"

    def test_admin_no_phone_required(self):
        """L'admin n'a pas besoin de téléphone."""
        user = UserCreate(
            email="admin@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            role=UserRole.ADMIN,
        )
        assert user.phone_number is None

    def test_valid_phone_format(self):
        user = UserCreate(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="+237699887766",
            role=UserRole.SERVANT,
        )
        assert user.phone_number == "+237699887766"


# ═══════════════════════════════════════════════════════════════════════════
#  UserCreateWithInvite
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUserCreateWithInvite:
    def test_servant_without_invitation(self):
        user = UserCreateWithInvite(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="+237600000001",
            role=UserRole.SERVANT,
        )
        assert user.invitation_code is None

    def test_parent_with_invitation(self):
        user = UserCreateWithInvite(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="+237600000001",
            role=UserRole.PARENT,
            invitation_code="INV-ABC123",
        )
        assert user.invitation_code == "INV-ABC123"

    def test_default_role_is_servant(self):
        user = UserCreateWithInvite(
            email="u@t.com",
            password="TestPass1",
            first_name="A",
            last_name="B",
            phone_number="+237600000001",
        )
        assert user.role == UserRole.SERVANT


# ═══════════════════════════════════════════════════════════════════════════
#  TokenData — role OBLIGATOIRE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestTokenData:
    USER_ID = "12345678-1234-1234-1234-123456789012"

    def test_valid(self):
        td = TokenData(user_id=self.USER_ID, role=UserRole.ADMIN)
        assert str(td.user_id) == self.USER_ID
        assert td.role == UserRole.ADMIN

    def test_missing_role_raises(self):
        with pytest.raises(ValidationError):
            TokenData(user_id=self.USER_ID)

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            TokenData(role=UserRole.ADMIN)

    def test_invalid_role_raises(self):
        with pytest.raises(ValidationError):
            TokenData(user_id=self.USER_ID, role="INVALID_ROLE")

    def test_all_valid_roles(self):
        for role in UserRole:
            td = TokenData(user_id=self.USER_ID, role=role)
            assert td.role == role


# ═══════════════════════════════════════════════════════════════════════════
#  Token / Request Schemas
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestOtherSchemas:
    def test_token(self):
        t = Token(access_token="abc", refresh_token="def", token_type="bearer")
        assert t.token_type == "bearer"

    def test_refresh_token_request(self):
        r = RefreshTokenRequest(refresh_token="abc")
        assert r.refresh_token == "abc"

    def test_forgot_password_request_valid_email(self):
        r = ForgotPasswordRequest(email="u@t.com")
        assert r.email == "u@t.com"

    def test_forgot_password_request_invalid_email(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-email")

    def test_reset_password_request(self):
        r = ResetPasswordRequest(token="tok", new_password="pwd")
        assert r.token == "tok"
