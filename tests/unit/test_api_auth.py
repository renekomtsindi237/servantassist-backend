"""
Unit tests for auth.py API router.
Uses FastAPI TestClient with mocked AuthService and dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_token_response():
    return {
        "access_token": "eyJhbGciOiJIUzI1NiJ9.test.sig",
        "refresh_token": "eyJhbGciOiJIUzI1NiJ9.refresh.sig",
        "token_type": "bearer",
    }


def _make_user(role="ADMIN"):
    from src.core.entities.user import UserRole

    user = MagicMock()
    user.id = uuid4()
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN if role == "ADMIN" else UserRole.SERVANT
    user.is_active = True
    return user


def _build_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.infrastructure.database.session import get_db_session
    from src.presentation.api.v1.auth import router
    from src.presentation.dependencies.auth_deps import get_current_active_user

    app = FastAPI()
    app.include_router(router, prefix="/auth")

    session = AsyncMock()
    current_user = _make_user("ADMIN")

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_db_session] = lambda: session

    return TestClient(app), session, current_user


# ─────────────────────────────────────────────────────────────────────────────
#  POST /login (OAuth2 form)
# ─────────────────────────────────────────────────────────────────────────────


def test_login_success():
    client, session, _ = _build_client()
    tokens = _make_token_response()
    mock_user = _make_user("ADMIN")

    mock_auth = MagicMock()
    mock_auth.authenticate_user = AsyncMock(return_value=mock_user)
    mock_auth.create_tokens = AsyncMock(return_value=tokens)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.presentation.api.v1.auth.brute_force_guard") as mock_bf:
                mock_bf.check_locked = AsyncMock(return_value=(False, 0))
                mock_bf.record_success = AsyncMock()
                with patch("src.presentation.api.v1.auth.asyncio.create_task"):
                    response = client.post(
                        "/auth/login",
                        data={"username": "admin@example.com", "password": "Password1!"},
                    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_brute_force_locked():
    client, session, _ = _build_client()

    with patch("src.presentation.api.v1.auth.brute_force_guard") as mock_bf:
        mock_bf.check_locked = AsyncMock(return_value=(True, 60))
        response = client.post(
            "/auth/login",
            data={"username": "admin@example.com", "password": "Password1!"},
        )

    assert response.status_code == 429


def test_login_auth_failure():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.authenticate_user = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.presentation.api.v1.auth.brute_force_guard") as mock_bf:
                mock_bf.check_locked = AsyncMock(return_value=(False, 0))
                mock_bf.record_failure = AsyncMock()
                response = client.post(
                    "/auth/login",
                    data={"username": "admin@example.com", "password": "wrong"},
                )

    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
#  POST /login/phone
# ─────────────────────────────────────────────────────────────────────────────


def test_login_phone_success():
    client, session, _ = _build_client()
    tokens = _make_token_response()
    mock_user = _make_user("SERVANT")

    mock_auth = MagicMock()
    mock_auth.authenticate_user = AsyncMock(return_value=mock_user)
    mock_auth.create_tokens = AsyncMock(return_value=tokens)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.presentation.api.v1.auth.brute_force_guard") as mock_bf:
                mock_bf.check_locked = AsyncMock(return_value=(False, 0))
                mock_bf.record_success = AsyncMock()
                with patch("src.presentation.api.v1.auth.asyncio.create_task"):
                    response = client.post(
                        "/auth/login/phone",
                        json={"phone_number": "+237600000000", "password": "Password1!"},
                    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_phone_brute_force_locked():
    client, session, _ = _build_client()

    with patch("src.presentation.api.v1.auth.brute_force_guard") as mock_bf:
        mock_bf.check_locked = AsyncMock(return_value=(True, 30))
        response = client.post(
            "/auth/login/phone",
            json={"phone_number": "+237600000000", "password": "Password1!"},
        )

    assert response.status_code == 429


# ─────────────────────────────────────────────────────────────────────────────
#  POST /register
# ─────────────────────────────────────────────────────────────────────────────


def test_register_admin_forbidden():
    client, session, _ = _build_client()

    response = client.post(
        "/auth/register",
        json={
            "email": "admin2@example.com",
            "password": "Password1!",
            "first_name": "Admin",
            "last_name": "Two",
            "role": "ADMIN",
            "phone_number": "+237600000001",
        },
    )

    assert response.status_code == 403


def test_register_servant_success():
    from src.core.entities.user import UserRole
    from src.presentation.schemas.auth import UserResponse

    client, session, _ = _build_client()
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.email = "servant@example.com"
    mock_user.first_name = "Jean"
    mock_user.last_name = "Dupont"
    mock_user.role = UserRole.SERVANT
    mock_user.is_active = True
    mock_user.profile_photo_url = None
    mock_user.phone_number = "+237600000002"

    mock_auth = MagicMock()
    mock_auth.register_user = AsyncMock(return_value=mock_user)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.presentation.api.v1.auth.InvitationCodeRepository"):
                response = client.post(
                    "/auth/register",
                    json={
                        "email": "servant@example.com",
                        "password": "Password1!",
                        "first_name": "Jean",
                        "last_name": "Dupont",
                        "role": "SERVANT",
                        "phone_number": "+237600000002",
                    },
                )

    assert response.status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
#  POST /refresh
# ─────────────────────────────────────────────────────────────────────────────


def test_refresh_token_success():
    client, session, _ = _build_client()
    tokens = _make_token_response()

    mock_auth = MagicMock()
    mock_auth.refresh_token = AsyncMock(return_value=tokens)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "eyJhbGciOiJIUzI1NiJ9.refresh.sig"},
            )

    assert response.status_code == 200
    assert "access_token" in response.json()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /logout
# ─────────────────────────────────────────────────────────────────────────────


def test_logout_no_bearer():
    client, session, _ = _build_client()
    response = client.post("/auth/logout")
    assert response.status_code == 400


def test_logout_success():
    client, session, _ = _build_client()

    with patch("src.presentation.api.v1.auth.token_blacklist") as mock_bl:
        mock_bl.revoke = AsyncMock()
        with patch("src.presentation.api.v1.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {"jti": "some-jti", "exp": 9999999999}
            with patch("src.presentation.api.v1.auth.get_settings") as mock_gs:
                settings = MagicMock()
                settings.JWT_SECRET_KEY = "secret"
                settings.JWT_ALGORITHM = "HS256"
                mock_gs.return_value = settings
                response = client.post(
                    "/auth/logout",
                    headers={"Authorization": "Bearer valid.token.here"},
                )

    assert response.status_code == 200
    assert "message" in response.json()


def test_logout_invalid_token_still_ok():
    """Even if JWT decode fails, logout returns 200."""
    import jwt as pyjwt

    client, session, _ = _build_client()

    with patch("src.presentation.api.v1.auth.jwt.decode", side_effect=pyjwt.PyJWTError("bad")):
        with patch("src.presentation.api.v1.auth.get_settings") as mock_gs:
            settings = MagicMock()
            settings.JWT_SECRET_KEY = "secret"
            settings.JWT_ALGORITHM = "HS256"
            mock_gs.return_value = settings
            response = client.post(
                "/auth/logout",
                headers={"Authorization": "Bearer bad.token.here"},
            )

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /forgot-password
# ─────────────────────────────────────────────────────────────────────────────


def test_forgot_password():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.forgot_password = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.infrastructure.services.email_service.EmailService"):
                response = client.post(
                    "/auth/forgot-password",
                    json={"email": "user@example.com"},
                )

    assert response.status_code == 200
    assert "message" in response.json()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /request-reset-code
# ─────────────────────────────────────────────────────────────────────────────


def test_request_reset_code():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.request_reset_code = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.infrastructure.services.email_service.EmailService"):
                with patch(
                    "src.infrastructure.repositories.password_reset_code_repository.PasswordResetCodeRepository",
                    create=True,
                ):
                    response = client.post(
                        "/auth/request-reset-code",
                        json={"email": "user@example.com"},
                    )

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /verify-reset-code
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_reset_code():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.verify_reset_code = AsyncMock(return_value="reset-token-here")

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch(
                "src.infrastructure.repositories.password_reset_code_repository.PasswordResetCodeRepository",
                create=True,
            ):
                response = client.post(
                    "/auth/verify-reset-code",
                    json={"email": "user@example.com", "code": "123456"},
                )

    assert response.status_code == 200
    data = response.json()
    assert "reset_token" in data


# ─────────────────────────────────────────────────────────────────────────────
#  POST /reset-password
# ─────────────────────────────────────────────────────────────────────────────


def test_reset_password():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.reset_password = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            with patch("src.infrastructure.services.email_service.EmailService"):
                response = client.post(
                    "/auth/reset-password",
                    json={"token": "valid-token", "new_password": "NewPass1!"},
                )

    assert response.status_code == 200
    assert "message" in response.json()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /request-reset-code/phone
# ─────────────────────────────────────────────────────────────────────────────


def test_request_reset_code_phone():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.request_reset_code_phone = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            response = client.post(
                "/auth/request-reset-code/phone",
                json={"phone_number": "+237600000000"},
            )

    assert response.status_code == 200
    assert "message" in response.json()


# ─────────────────────────────────────────────────────────────────────────────
#  POST /verify-reset-code/phone
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_reset_code_phone():
    client, session, _ = _build_client()

    mock_auth = MagicMock()
    mock_auth.verify_reset_code_phone = AsyncMock(return_value="phone-reset-token")

    with patch("src.presentation.api.v1.auth.AuthService", return_value=mock_auth):
        with patch("src.presentation.api.v1.auth.UserRepository"):
            response = client.post(
                "/auth/verify-reset-code/phone",
                json={"phone_number": "+237600000000", "code": "654321"},
            )

    assert response.status_code == 200
    assert "reset_token" in response.json()


# ─────────────────────────────────────────────────────────────────────────────
#  GET /server-pubkey
# ─────────────────────────────────────────────────────────────────────────────


def test_get_server_pubkey():
    client, session, _ = _build_client()

    mock_encryptor = MagicMock()
    mock_encryptor.public_key_b64 = "base64urlpubkey=="

    with patch("src.presentation.api.v1.auth.get_settings") as mock_gs:
        settings = MagicMock()
        settings.PAYLOAD_ENCRYPTION_PRIVATE_KEY = "fake-ec-private-key-for-test"
        mock_gs.return_value = settings
        with patch(
            "src.infrastructure.security.payload_encryption.get_payload_encryptor",
            return_value=mock_encryptor,
        ):
            response = client.get("/auth/server-pubkey")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["key"] == "base64urlpubkey=="
