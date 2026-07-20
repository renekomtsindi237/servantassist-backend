"""
Unit tests for users.py API router.
Uses FastAPI TestClient with dependency overrides.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_profile_response(role="SERVANT"):
    """Create a real UserProfileResponse instance."""
    from src.core.entities.user import UserRole
    from src.presentation.schemas.user import UserProfileResponse

    return UserProfileResponse(
        id=uuid4(),
        email="jean@example.com",
        first_name="Jean",
        last_name="Dupont",
        role=UserRole.SERVANT if role == "SERVANT" else UserRole.ADMIN,
        is_active=True,
    )


def _make_user_entity(role_value="SERVANT"):
    from src.core.entities.user import UserRole

    user = MagicMock()
    user.id = uuid4()
    user.role = {
        "ADMIN": UserRole.ADMIN,
        "SERVANT": UserRole.SERVANT,
        "PARENT": UserRole.PARENT,
        "AUMONIER": UserRole.AUMÔNIER,
    }.get(role_value, UserRole.SERVANT)
    user.first_name = "Jean"
    user.last_name = "Dupont"
    user.email = "jean@example.com"
    user.phone_number = "+237600000000"
    user.is_active = True
    user.profile_photo_url = None
    user.terms_accepted_at = None
    user.data_consent_at = None
    return user


def _build_client(current_user=None, mock_session=None, role="ADMIN"):
    """Build a TestClient with dependency overrides."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from src.presentation.api.v1.users import router
    from src.presentation.dependencies.auth_deps import (
        get_current_active_user,
        get_current_admin_or_aumonier,
        get_current_admin_user,
    )
    from src.infrastructure.database.session import get_db_session

    app = FastAPI()
    app.include_router(router, prefix="/users")

    if current_user is None:
        current_user = _make_user_entity(role)

    if mock_session is None:
        mock_session = AsyncMock()

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_current_admin_or_aumonier] = lambda: current_user
    app.dependency_overrides[get_current_admin_user] = lambda: current_user
    app.dependency_overrides[get_db_session] = lambda: mock_session

    return TestClient(app), current_user, mock_session


# ─────────────────────────────────────────────────────────────────────────────
#  GET /me
# ─────────────────────────────────────────────────────────────────────────────

def test_get_my_profile_servant():
    client, user, session = _build_client(role="SERVANT")
    profile = _make_profile_response("SERVANT")

    mock_nom_repo = MagicMock()
    mock_nom_repo.get_active_by_user = AsyncMock(return_value=[])
    mock_user_repo = MagicMock()
    mock_user_repo.get_parents_of = AsyncMock(return_value=[])

    with patch("src.presentation.api.v1.users.NominationRepository", return_value=mock_nom_repo):
        with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
            with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
                mock_cls.model_validate.return_value = profile
                response = client.get("/users/me")

    assert response.status_code == 200


def test_get_my_profile_non_servant():
    client, user, session = _build_client(role="ADMIN")
    profile = _make_profile_response("ADMIN")

    with patch("src.presentation.api.v1.users.NominationRepository"):
        with patch("src.presentation.api.v1.users.UserRepository"):
            with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
                mock_cls.model_validate.return_value = profile
                response = client.get("/users/me")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /me
# ─────────────────────────────────────────────────────────────────────────────

def test_update_my_profile():
    profile = _make_profile_response("SERVANT")
    client, user, session = _build_client(role="SERVANT")

    mock_service = MagicMock()
    mock_service.update_profile = AsyncMock(return_value=profile)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch("/users/me", json={"first_name": "Marc"})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /me/password
# ─────────────────────────────────────────────────────────────────────────────

def test_change_my_password():
    client, user, session = _build_client(role="SERVANT")

    mock_service = MagicMock()
    mock_service.change_password = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch(
                "/users/me/password",
                json={"current_password": "OldPass1!", "new_password": "NewPass1!"},
            )

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /me/photo
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_my_photo_no_photo():
    user = _make_user_entity("SERVANT")
    user.profile_photo_url = None
    client, _, session = _build_client(current_user=user)

    response = client.delete("/users/me/photo")
    assert response.status_code == 404


def test_delete_my_photo_success():
    user = _make_user_entity("SERVANT")
    user.profile_photo_url = "https://example.com/photo.jpg"
    client, _, session = _build_client(current_user=user)

    mock_storage = MagicMock()
    mock_storage.delete_file = AsyncMock(return_value=None)
    mock_user_repo = MagicMock()
    mock_user_repo.update = AsyncMock(return_value=user)

    with patch("src.presentation.api.v1.users.StorageService", return_value=mock_storage):
        with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
            response = client.delete("/users/me/photo")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  POST /me/link-parent
# ─────────────────────────────────────────────────────────────────────────────

def test_self_link_parent_non_servant():
    client, user, session = _build_client(role="PARENT")
    response = client.post("/users/me/link-parent", json={"parent_phone": "+237600000001"})
    assert response.status_code == 403


def test_self_link_parent_parent_not_found():
    client, user, session = _build_client(role="SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.get_by_phone = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        response = client.post("/users/me/link-parent", json={"parent_phone": "+237600000001"})

    assert response.status_code == 404


def test_self_link_parent_success():
    from src.core.entities.user import UserRole

    client, user, session = _build_client(role="SERVANT")
    parent = _make_user_entity("PARENT")
    parent.role = UserRole.PARENT

    profile = _make_profile_response("SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.get_by_phone = AsyncMock(return_value=parent)
    mock_user_repo.add_parent_link = AsyncMock(return_value=None)
    mock_user_repo.get = AsyncMock(return_value=user)
    mock_user_repo.get_parents_of = AsyncMock(return_value=[parent])

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
            inst = MagicMock(spec=profile)
            inst.parent_ids = []
            mock_cls.model_validate.return_value = profile
            response = client.post("/users/me/link-parent", json={"parent_phone": "+237600000001"})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /me/link-parent/{parent_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_self_unlink_parent_non_servant():
    client, user, session = _build_client(role="PARENT")
    response = client.delete(f"/users/me/link-parent/{uuid4()}")
    assert response.status_code == 403


def test_self_unlink_parent_success():
    client, user, session = _build_client(role="SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.remove_parent_link = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        response = client.delete(f"/users/me/link-parent/{uuid4()}")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  GET /directory
# ─────────────────────────────────────────────────────────────────────────────

def test_list_directory():
    client, user, session = _build_client(role="SERVANT")

    mock_service = MagicMock()
    mock_service.list_users = AsyncMock(return_value={
        "items": [], "total": 0, "page": 1, "page_size": 50, "total_pages": 0, "links": None
    })

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.get("/users/directory")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET / (admin list)
# ─────────────────────────────────────────────────────────────────────────────

def test_list_users_admin():
    client, user, session = _build_client(role="ADMIN")

    mock_service = MagicMock()
    mock_service.list_users = AsyncMock(return_value={
        "items": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0, "links": None
    })

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.get("/users/")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{user_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_get_user():
    client, user, session = _build_client(role="ADMIN")
    target = _make_user_entity("SERVANT")
    profile = _make_profile_response("SERVANT")

    mock_service = MagicMock()
    mock_service.get_user = AsyncMock(return_value=target)
    mock_user_repo = MagicMock()
    mock_user_repo.get_parents_of = AsyncMock(return_value=[])

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
            with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
                mock_cls.model_validate.return_value = profile
                response = client.get(f"/users/{target.id}")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{user_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_update_user():
    client, user, session = _build_client(role="ADMIN")
    profile = _make_profile_response("ADMIN")

    mock_service = MagicMock()
    mock_service.admin_update_user = AsyncMock(return_value=profile)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch(f"/users/{uuid4()}", json={"first_name": "Admin"})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{user_id}/activate & /deactivate
# ─────────────────────────────────────────────────────────────────────────────

def test_activate_user():
    client, user, session = _build_client(role="ADMIN")
    profile = _make_profile_response("ADMIN")

    mock_service = MagicMock()
    mock_service.activate_user = AsyncMock(return_value=profile)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch(f"/users/{uuid4()}/activate")

    assert response.status_code == 200


def test_deactivate_user():
    client, user, session = _build_client(role="ADMIN")
    profile = _make_profile_response("ADMIN")

    mock_service = MagicMock()
    mock_service.deactivate_user = AsyncMock(return_value=profile)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch(f"/users/{uuid4()}/deactivate")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{user_id}/reset-password
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_reset_password():
    client, user, session = _build_client(role="ADMIN")

    mock_service = MagicMock()
    mock_service.admin_reset_password = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.post(f"/users/{uuid4()}/reset-password", json={"new_password": "NewPass1!"})

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /{user_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_user():
    client, user, session = _build_client(role="ADMIN")

    mock_service = MagicMock()
    mock_service.delete_user = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.delete(f"/users/{uuid4()}")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  POST /me/accept-terms & /me/data-consent
# ─────────────────────────────────────────────────────────────────────────────

def test_accept_terms():
    client, user, session = _build_client(role="SERVANT")
    profile = _make_profile_response("SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.update = AsyncMock(return_value=user)

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
            mock_cls.model_validate.return_value = profile
            response = client.post("/users/me/accept-terms")

    assert response.status_code == 200


def test_record_data_consent():
    client, user, session = _build_client(role="SERVANT")
    profile = _make_profile_response("SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.update = AsyncMock(return_value=user)

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
            mock_cls.model_validate.return_value = profile
            response = client.post("/users/me/data-consent")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{user_id}/children
# ─────────────────────────────────────────────────────────────────────────────

def test_get_user_children():
    client, user, session = _build_client(role="ADMIN")
    child = _make_user_entity("SERVANT")
    profile = _make_profile_response("SERVANT")

    mock_user_repo = MagicMock()
    mock_user_repo.get_children_of = AsyncMock(return_value=[child])

    with patch("src.presentation.api.v1.users.UserRepository", return_value=mock_user_repo):
        with patch("src.presentation.api.v1.users.UserProfileResponse") as mock_cls:
            mock_cls.model_validate.return_value = profile
            response = client.get(f"/users/{uuid4()}/children")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{user_id}/link-parent
# ─────────────────────────────────────────────────────────────────────────────

def test_link_parent():
    client, user, session = _build_client(role="ADMIN")
    target_id = uuid4()
    parent_id = uuid4()
    profile = _make_profile_response("ADMIN")

    mock_service = MagicMock()
    mock_service.link_parent = AsyncMock(return_value=profile)

    with patch("src.presentation.api.v1.users.UserService", return_value=mock_service):
        with patch("src.presentation.api.v1.users.UserRepository"):
            response = client.patch(
                f"/users/{target_id}/link-parent",
                json={"parent_id": str(parent_id), "unlink": False}
            )

    assert response.status_code == 200
