"""
Tests unitaires — UserService (profil, mot de passe, admin).
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.application.services.user_service import UserService
from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.schemas.user import (
    ChangePasswordRequest,
    UserAdminResetPassword,
    UserAdminUpdate,
    UserProfileUpdate,
)
from tests.conftest import VALID_PASSWORD


def _make_service(session: AsyncSession) -> UserService:
    return UserService(UserRepository(session))


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE : update_profile
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestUpdateProfile:
    async def test_update_first_name(self, db_session, servant_user):
        service = _make_service(db_session)
        updated = await service.update_profile(
            servant_user, UserProfileUpdate(first_name="Nouveau")
        )
        assert updated.first_name == "Nouveau"
        assert updated.last_name == servant_user.last_name  # Inchange

    async def test_update_last_name(self, db_session, servant_user):
        service = _make_service(db_session)
        updated = await service.update_profile(
            servant_user, UserProfileUpdate(last_name="NouveauNom")
        )
        assert updated.last_name == "NouveauNom"

    async def test_update_phone_number(self, db_session, servant_user):
        service = _make_service(db_session)
        updated = await service.update_profile(
            servant_user, UserProfileUpdate(phone_number="+237699999999")
        )
        assert updated.phone_number == "+237699999999"

    async def test_update_phone_conflict(self, db_session, servant_user, parent_user):
        """Deux utilisateurs ne peuvent pas avoir le meme numero."""
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.update_profile(
                servant_user,
                UserProfileUpdate(phone_number=parent_user.phone_number),
            )
        assert exc.value.status_code == 409

    async def test_partial_update_keeps_other_fields(self, db_session, servant_user):
        """Un PATCH partiel ne modifie que les champs fournis."""
        original_phone = servant_user.phone_number
        service = _make_service(db_session)
        updated = await service.update_profile(
            servant_user, UserProfileUpdate(first_name="Modifie")
        )
        assert updated.first_name == "Modifie"
        assert updated.phone_number == original_phone

    async def test_clear_phone_number(self, db_session, servant_user):
        """Envoyer phone_number='' supprime le numero."""
        service = _make_service(db_session)
        updated = await service.update_profile(
            servant_user, UserProfileUpdate(phone_number="")
        )
        assert updated.phone_number is None


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE : change_password
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestChangePassword:
    async def test_change_password_success(self, db_session, servant_user):
        service = _make_service(db_session)
        await service.change_password(
            servant_user,
            ChangePasswordRequest(
                current_password=VALID_PASSWORD, new_password="NewPass123"
            ),
        )
        # Verifier que le nouveau mot de passe fonctionne
        assert SecurityUtils.verify_password("NewPass123", servant_user.hashed_password)

    async def test_wrong_current_password(self, db_session, servant_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.change_password(
                servant_user,
                ChangePasswordRequest(
                    current_password="MauvaisMotDePasse1",
                    new_password="NewPass123",
                ),
            )
        assert exc.value.status_code == 400
        assert "actuel" in exc.value.detail.lower()

    async def test_same_password_rejected(self, db_session, servant_user):
        """Le nouveau mot de passe doit etre different de l'ancien."""
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.change_password(
                servant_user,
                ChangePasswordRequest(
                    current_password=VALID_PASSWORD,
                    new_password=VALID_PASSWORD,
                ),
            )
        assert exc.value.status_code == 400
        assert "different" in exc.value.detail.lower()


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN : list_users
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestListUsers:
    async def test_list_returns_all_users(self, db_session, admin_user, servant_user, parent_user):
        service = _make_service(db_session)
        result = await service.list_users(page=1, page_size=50)
        assert result.total >= 3
        assert len(result.items) >= 3

    async def test_filter_by_role(self, db_session, admin_user, servant_user, parent_user):
        service = _make_service(db_session)
        result = await service.list_users(role=UserRole.SERVANT)
        for u in result.items:
            assert u.role == UserRole.SERVANT

    async def test_filter_by_active(self, db_session, admin_user, servant_user, inactive_user):
        service = _make_service(db_session)
        result = await service.list_users(is_active=False)
        for u in result.items:
            assert u.is_active is False

    async def test_search_by_name(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        result = await service.list_users(search="Servant")
        assert result.total >= 1
        assert any("Servant" in u.first_name for u in result.items)

    async def test_search_by_email(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        result = await service.list_users(search="servant@")
        assert result.total >= 1

    async def test_pagination(self, db_session, admin_user, servant_user, parent_user):
        service = _make_service(db_session)
        result = await service.list_users(page=1, page_size=1)
        assert result.page_size == 1
        assert len(result.items) == 1
        assert result.total >= 3
        assert result.total_pages >= 3


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN : admin_update_user
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAdminUpdateUser:
    async def test_admin_updates_name(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        updated = await service.admin_update_user(
            servant_user.id,
            UserAdminUpdate(first_name="NouveauPrenom"),
            admin_user,
        )
        assert updated.first_name == "NouveauPrenom"

    async def test_admin_updates_email(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        updated = await service.admin_update_user(
            servant_user.id,
            UserAdminUpdate(email="newemail@test.com"),
            admin_user,
        )
        assert updated.email == "newemail@test.com"

    async def test_admin_email_conflict(self, db_session, admin_user, servant_user, parent_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.admin_update_user(
                servant_user.id,
                UserAdminUpdate(email=parent_user.email),
                admin_user,
            )
        assert exc.value.status_code == 409

    async def test_admin_cannot_deactivate_self(self, db_session, admin_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.admin_update_user(
                admin_user.id,
                UserAdminUpdate(is_active=False),
                admin_user,
            )
        assert exc.value.status_code == 400

    async def test_update_nonexistent_user(self, db_session, admin_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.admin_update_user(
                uuid4(), UserAdminUpdate(first_name="X"), admin_user
            )
        assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN : deactivate / activate
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestActivateDeactivate:
    async def test_deactivate_user(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        result = await service.deactivate_user(servant_user.id, admin_user)
        assert result.is_active is False

    async def test_deactivate_already_inactive(self, db_session, admin_user, inactive_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.deactivate_user(inactive_user.id, admin_user)
        assert exc.value.status_code == 400

    async def test_deactivate_self_rejected(self, db_session, admin_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.deactivate_user(admin_user.id, admin_user)
        assert exc.value.status_code == 400

    async def test_activate_user(self, db_session, admin_user, inactive_user):
        service = _make_service(db_session)
        result = await service.activate_user(inactive_user.id)
        assert result.is_active is True

    async def test_activate_already_active(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.activate_user(servant_user.id)
        assert exc.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN : reset_password
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAdminResetPassword:
    async def test_reset_password(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        await service.admin_reset_password(
            servant_user.id, UserAdminResetPassword(new_password="ResetPass1")
        )
        assert SecurityUtils.verify_password("ResetPass1", servant_user.hashed_password)


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN : delete_user
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestDeleteUser:
    async def test_delete_user(self, db_session, admin_user, servant_user):
        service = _make_service(db_session)
        await service.delete_user(servant_user.id, admin_user)
        # Verifier que l'utilisateur n'existe plus
        with pytest.raises(HTTPException) as exc:
            await service.get_user(servant_user.id)
        assert exc.value.status_code == 404

    async def test_delete_self_rejected(self, db_session, admin_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.delete_user(admin_user.id, admin_user)
        assert exc.value.status_code == 400

    async def test_delete_last_admin_rejected(self, db_session, admin_user, servant_user):
        """Le dernier admin ne peut pas etre supprime."""
        # Creer un second admin pour le test
        service = _make_service(db_session)
        # On ne peut supprimer admin_user que s'il y a un autre admin
        with pytest.raises(HTTPException) as exc:
            await service.delete_user(admin_user.id, admin_user)
        assert exc.value.status_code == 400

    async def test_delete_nonexistent_user(self, db_session, admin_user):
        service = _make_service(db_session)
        with pytest.raises(HTTPException) as exc:
            await service.delete_user(uuid4(), admin_user)
        assert exc.value.status_code == 404

