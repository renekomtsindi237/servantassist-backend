"""
Unit tests for UserService - covers the low-coverage methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


def _make_user(**kw):
    from src.core.entities.user import User, UserRole

    u = MagicMock(spec=User)
    u.id = kw.get("id", uuid4())
    u.email = kw.get("email", "user@example.com")
    u.phone_number = kw.get("phone_number", "+237600000000")
    u.first_name = kw.get("first_name", "Jean")
    u.last_name = kw.get("last_name", "Dupont")
    u.role = kw.get("role", UserRole.SERVANT)
    u.is_active = kw.get("is_active", True)
    u.hashed_password = kw.get("hashed_password", "$2b$hash")
    u.updated_at = kw.get("updated_at", None)
    u.position = kw.get("position", None)
    u.birth_date = kw.get("birth_date", None)
    return u


def _make_service(repo=None):
    from src.application.services.user_service import UserService

    if repo is None:
        repo = AsyncMock()
    return UserService(repo)


# ─── get_profile ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile():
    service = _make_service()
    user = _make_user()

    result = await service.get_profile(user)
    assert result is user


# ─── update_profile ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_profile_no_changes():
    repo = AsyncMock()
    repo.update = AsyncMock(return_value=_make_user())
    service = _make_service(repo)

    user = _make_user()
    from src.presentation.schemas.user import UserProfileUpdate
    data = UserProfileUpdate()

    result = await service.update_profile(user, data)
    repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_profile_email_conflict():
    repo = AsyncMock()
    repo.email_exists = AsyncMock(return_value=True)
    service = _make_service(repo)

    user = _make_user(email="old@example.com")
    from src.presentation.schemas.user import UserProfileUpdate
    data = UserProfileUpdate(email="new@example.com")

    with pytest.raises(HTTPException) as exc:
        await service.update_profile(user, data)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_profile_phone_conflict():
    repo = AsyncMock()
    repo.email_exists = AsyncMock(return_value=False)
    repo.phone_exists = AsyncMock(return_value=True)
    service = _make_service(repo)

    user = _make_user(phone_number="+237600000001")
    from src.presentation.schemas.user import UserProfileUpdate
    data = UserProfileUpdate(phone_number="+237600000002")

    with pytest.raises(HTTPException) as exc:
        await service.update_profile(user, data)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_profile_update_all_fields():
    repo = AsyncMock()
    repo.email_exists = AsyncMock(return_value=False)
    repo.phone_exists = AsyncMock(return_value=False)
    updated = _make_user(first_name="Pierre")
    repo.update = AsyncMock(return_value=updated)
    service = _make_service(repo)

    user = _make_user()
    from src.presentation.schemas.user import UserProfileUpdate
    data = UserProfileUpdate(
        first_name="Pierre",
        last_name="Durand",
        phone_number="+237600099999",
        email="pierre@example.com",
    )

    result = await service.update_profile(user, data)
    assert result is updated


@pytest.mark.asyncio
async def test_update_profile_clear_phone():
    """Setting phone_number to empty string clears it."""
    repo = AsyncMock()
    repo.update = AsyncMock(return_value=_make_user())
    service = _make_service(repo)

    user = _make_user(phone_number="+237600000001")
    from src.presentation.schemas.user import UserProfileUpdate
    data = UserProfileUpdate(phone_number="")

    await service.update_profile(user, data)
    assert user.phone_number is None


# ─── change_password ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    from src.presentation.schemas.user import ChangePasswordRequest

    repo = AsyncMock()
    service = _make_service(repo)
    user = _make_user()

    data = ChangePasswordRequest(current_password="wrong", new_password="NewPass123!")

    with patch("src.application.services.user_service.SecurityUtils.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await service.change_password(user, data)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_same_as_current():
    from src.presentation.schemas.user import ChangePasswordRequest

    repo = AsyncMock()
    service = _make_service(repo)
    user = _make_user()

    data = ChangePasswordRequest(current_password="OldPass123!", new_password="OldPass123!")

    # First call returns True (current ok), second returns True (same as current)
    with patch("src.application.services.user_service.SecurityUtils.verify_password", side_effect=[True, True]):
        with pytest.raises(HTTPException) as exc:
            await service.change_password(user, data)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_success():
    from src.presentation.schemas.user import ChangePasswordRequest

    repo = AsyncMock()
    repo.update = AsyncMock()
    service = _make_service(repo)
    user = _make_user()

    data = ChangePasswordRequest(current_password="OldPass123!", new_password="NewPass456!")

    with patch("src.application.services.user_service.SecurityUtils.verify_password", side_effect=[True, False]):
        with patch("src.application.services.user_service.SecurityUtils.get_password_hash", return_value="newhash"):
            await service.change_password(user, data)

    repo.update.assert_called_once()
    assert user.hashed_password == "newhash"


# ─── list_users ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    users = [_make_user(), _make_user()]
    repo.list_paginated = AsyncMock(return_value=(users, 2))
    service = _make_service(repo)

    # Need UserProfileResponse to be able to model_validate
    with patch("src.application.services.user_service.UserProfileResponse") as mock_resp:
        mock_resp.model_validate = MagicMock(return_value=MagicMock())
        result = await service.list_users(page=1, page_size=20)

    assert result.total == 2
    assert result.page == 1


# ─── get_user ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_found():
    repo = AsyncMock()
    user = _make_user()
    repo.get = AsyncMock(return_value=user)
    service = _make_service(repo)

    result = await service.get_user(user.id)
    assert result is user


@pytest.mark.asyncio
async def test_get_user_not_found():
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=None)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.get_user(uuid4())
    assert exc.value.status_code == 404


# ─── admin_update_user ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_update_user_basic():
    from src.presentation.schemas.user import UserAdminUpdate

    repo = AsyncMock()
    user = _make_user()
    admin = _make_user(id=uuid4())
    repo.get = AsyncMock(return_value=user)
    repo.email_exists = AsyncMock(return_value=False)
    repo.update = AsyncMock(return_value=user)
    service = _make_service(repo)

    data = UserAdminUpdate(first_name="Updated")

    result = await service.admin_update_user(user.id, data, admin)
    assert result is user


@pytest.mark.asyncio
async def test_admin_update_user_cannot_deactivate_self():
    from src.presentation.schemas.user import UserAdminUpdate

    repo = AsyncMock()
    admin = _make_user()
    repo.get = AsyncMock(return_value=admin)
    service = _make_service(repo)

    data = UserAdminUpdate(is_active=False)

    with pytest.raises(HTTPException) as exc:
        await service.admin_update_user(admin.id, data, admin)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_admin_update_user_email_conflict():
    from src.presentation.schemas.user import UserAdminUpdate

    repo = AsyncMock()
    user = _make_user(email="old@example.com")
    admin = _make_user(id=uuid4())
    repo.get = AsyncMock(return_value=user)
    repo.email_exists = AsyncMock(return_value=True)
    service = _make_service(repo)

    data = UserAdminUpdate(email="new@example.com")

    with pytest.raises(HTTPException) as exc:
        await service.admin_update_user(user.id, data, admin)
    assert exc.value.status_code == 409


# ─── link_parent ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_parent_not_servant():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    user = _make_user(role=UserRole.PARENT)  # not SERVANT
    repo.get = AsyncMock(return_value=user)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.link_parent(user.id, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_link_parent_no_parent_id():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    servant = _make_user(role=UserRole.SERVANT)
    repo.get = AsyncMock(return_value=servant)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.link_parent(servant.id, None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_link_parent_target_not_parent_role():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    servant = _make_user(role=UserRole.SERVANT)
    non_parent = _make_user(role=UserRole.SERVANT)
    repo.get = AsyncMock(side_effect=[servant, non_parent, servant])
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.link_parent(servant.id, non_parent.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_link_parent_success():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    servant = _make_user(role=UserRole.SERVANT)
    parent = _make_user(role=UserRole.PARENT)
    repo.get = AsyncMock(side_effect=[servant, parent, servant])
    repo.add_parent_link = AsyncMock()
    service = _make_service(repo)

    result = await service.link_parent(servant.id, parent.id)
    repo.add_parent_link.assert_called_once_with(servant.id, parent.id)


@pytest.mark.asyncio
async def test_unlink_parent_no_parent_id():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    servant = _make_user(role=UserRole.SERVANT)
    repo.get = AsyncMock(return_value=servant)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.link_parent(servant.id, None, unlink=True)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unlink_parent_success():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    servant = _make_user(role=UserRole.SERVANT)
    repo.get = AsyncMock(side_effect=[servant, servant])
    repo.remove_parent_link = AsyncMock()
    service = _make_service(repo)

    result = await service.link_parent(servant.id, uuid4(), unlink=True)
    repo.remove_parent_link.assert_called_once()


# ─── deactivate_user ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deactivate_user_self():
    repo = AsyncMock()
    admin = _make_user()
    repo.get = AsyncMock(return_value=admin)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.deactivate_user(admin.id, admin)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_deactivate_user_already_inactive():
    repo = AsyncMock()
    user = _make_user(is_active=False)
    admin = _make_user()
    repo.get = AsyncMock(return_value=user)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.deactivate_user(user.id, admin)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_deactivate_user_success():
    repo = AsyncMock()
    user = _make_user(is_active=True)
    admin = _make_user(id=uuid4())
    repo.get = AsyncMock(return_value=user)
    repo.update = AsyncMock(return_value=user)
    service = _make_service(repo)

    with patch("src.application.services.user_service.event_bus.publish", new_callable=AsyncMock):
        result = await service.deactivate_user(user.id, admin)

    assert user.is_active is False


# ─── activate_user ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activate_user_already_active():
    repo = AsyncMock()
    user = _make_user(is_active=True)
    repo.get = AsyncMock(return_value=user)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.activate_user(user.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_activate_user_success():
    repo = AsyncMock()
    user = _make_user(is_active=False)
    repo.get = AsyncMock(return_value=user)
    repo.update = AsyncMock(return_value=user)
    service = _make_service(repo)

    with patch("src.application.services.user_service.event_bus.publish", new_callable=AsyncMock):
        result = await service.activate_user(user.id)

    assert user.is_active is True


# ─── admin_reset_password ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_reset_password():
    from src.presentation.schemas.user import UserAdminResetPassword

    repo = AsyncMock()
    user = _make_user()
    repo.get = AsyncMock(return_value=user)
    repo.update = AsyncMock()
    service = _make_service(repo)

    data = UserAdminResetPassword(new_password="NewSecure456!")

    with patch("src.application.services.user_service.SecurityUtils.get_password_hash", return_value="newhash"):
        with patch("src.application.services.user_service.event_bus.publish", new_callable=AsyncMock):
            await service.admin_reset_password(user.id, data)

    assert user.hashed_password == "newhash"


# ─── delete_user ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_user_self():
    repo = AsyncMock()
    admin = _make_user()
    repo.get = AsyncMock(return_value=admin)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.delete_user(admin.id, admin)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_user_last_admin():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    admin_to_delete = _make_user(role=UserRole.ADMIN)
    admin = _make_user(id=uuid4(), role=UserRole.ADMIN)
    repo.get = AsyncMock(return_value=admin_to_delete)
    repo.count_by_role = AsyncMock(return_value=1)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.delete_user(admin_to_delete.id, admin)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_user_success():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    user = _make_user(role=UserRole.SERVANT)
    admin = _make_user(id=uuid4(), role=UserRole.ADMIN)
    repo.get = AsyncMock(return_value=user)
    repo.delete = AsyncMock(return_value=True)
    service = _make_service(repo)

    with patch("src.application.services.user_service.event_bus.publish", new_callable=AsyncMock):
        await service.delete_user(user.id, admin)

    repo.delete.assert_called_once_with(user.id)


@pytest.mark.asyncio
async def test_delete_user_delete_fails():
    from src.core.entities.user import UserRole

    repo = AsyncMock()
    user = _make_user(role=UserRole.SERVANT)
    admin = _make_user(id=uuid4(), role=UserRole.ADMIN)
    repo.get = AsyncMock(return_value=user)
    repo.delete = AsyncMock(return_value=False)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.delete_user(user.id, admin)
    assert exc.value.status_code == 500
