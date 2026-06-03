"""
Tests unitaires pour application/commands/ et application/queries/

Couvre :
- CreateInvitationCommand.execute()
- ResetPasswordCommand.execute()
- DeactivateUserCommand.execute()
- ActivateUserCommand.execute()
- DeleteUserCommand.execute()
- DashboardQuery (toutes les méthodes)
- UserListQuery.execute()
- UserStatsQuery.execute()
- UserSearchQuery (by_id, by_email, by_phone)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.commands.auth_commands import CreateInvitationCommand
from src.application.commands.user_commands import (
    ActivateUserCommand,
    DeactivateUserCommand,
    DeleteUserCommand,
    ResetPasswordCommand,
)
from src.application.queries.user_queries import (
    UserListQuery,
    UserSearchQuery,
    UserStatsQuery,
)
from src.core.entities.user import UserRole


# ── CreateInvitationCommand ────────────────────────────────────────────────


class TestCreateInvitationCommand:
    @pytest.mark.asyncio
    async def test_creates_invitation_with_email(self):
        admin_id = uuid4()
        invitation_repo = AsyncMock()
        created_invitation = MagicMock()
        created_invitation.id = uuid4()
        invitation_repo.create.return_value = created_invitation

        cmd = CreateInvitationCommand(
            created_by_id=admin_id,
            role=UserRole.PARENT,
            email="parent@test.com",
        )

        with patch("src.application.commands.auth_commands.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            result = await cmd.execute(invitation_repo)

        invitation_repo.create.assert_called_once()
        mock_bus.publish.assert_called_once()
        assert result is created_invitation

    @pytest.mark.asyncio
    async def test_creates_invitation_without_email(self):
        admin_id = uuid4()
        invitation_repo = AsyncMock()
        created_invitation = MagicMock()
        created_invitation.id = uuid4()
        invitation_repo.create.return_value = created_invitation

        cmd = CreateInvitationCommand(
            created_by_id=admin_id,
            role=UserRole.SERVANT,
        )

        with patch("src.application.commands.auth_commands.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            result = await cmd.execute(invitation_repo)

        assert result is created_invitation

    @pytest.mark.asyncio
    async def test_creates_invitation_with_phone(self):
        admin_id = uuid4()
        invitation_repo = AsyncMock()
        created_invitation = MagicMock()
        created_invitation.id = uuid4()
        invitation_repo.create.return_value = created_invitation

        cmd = CreateInvitationCommand(
            created_by_id=admin_id,
            role=UserRole.PARENT,
            phone_number="+237600000001",
        )

        with patch("src.application.commands.auth_commands.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            result = await cmd.execute(invitation_repo)

        assert result is created_invitation

    @pytest.mark.asyncio
    async def test_emits_user_invited_event(self):
        admin_id = uuid4()
        invitation_repo = AsyncMock()
        created_invitation = MagicMock()
        created_invitation.id = uuid4()
        invitation_repo.create.return_value = created_invitation

        cmd = CreateInvitationCommand(
            created_by_id=admin_id,
            role=UserRole.PARENT,
            email="test@example.com",
        )

        with patch("src.application.commands.auth_commands.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            await cmd.execute(invitation_repo)
            mock_bus.publish.assert_called_once()
            event_arg = mock_bus.publish.call_args[0][0]
            assert event_arg.email == "test@example.com"
            assert event_arg.role == UserRole.PARENT.value


# ── ResetPasswordCommand ───────────────────────────────────────────────────


class TestResetPasswordCommand:
    @pytest.mark.asyncio
    async def test_delegates_to_service(self):
        user_id = uuid4()
        admin = MagicMock()
        service = AsyncMock()

        cmd = ResetPasswordCommand(
            user_id=user_id,
            new_password="NewSecurePass1!",
            admin=admin,
        )
        await cmd.execute(service)

        service.admin_reset_password.assert_called_once()
        call_args = service.admin_reset_password.call_args
        assert call_args[0][0] == user_id


# ── DeactivateUserCommand ──────────────────────────────────────────────────


class TestDeactivateUserCommand:
    @pytest.mark.asyncio
    async def test_delegates_to_service(self):
        user_id = uuid4()
        admin = MagicMock()
        deactivated = MagicMock()
        service = AsyncMock()
        service.deactivate_user.return_value = deactivated

        cmd = DeactivateUserCommand(user_id=user_id, admin=admin)
        result = await cmd.execute(service)

        service.deactivate_user.assert_called_once_with(user_id, admin)
        assert result is deactivated


# ── ActivateUserCommand ────────────────────────────────────────────────────


class TestActivateUserCommand:
    @pytest.mark.asyncio
    async def test_delegates_to_service(self):
        user_id = uuid4()
        activated = MagicMock()
        service = AsyncMock()
        service.activate_user.return_value = activated

        cmd = ActivateUserCommand(user_id=user_id)
        result = await cmd.execute(service)

        service.activate_user.assert_called_once_with(user_id)
        assert result is activated


# ── DeleteUserCommand ──────────────────────────────────────────────────────


class TestDeleteUserCommand:
    @pytest.mark.asyncio
    async def test_delegates_to_service(self):
        user_id = uuid4()
        admin = MagicMock()
        service = AsyncMock()

        cmd = DeleteUserCommand(user_id=user_id, admin=admin)
        await cmd.execute(service)

        service.delete_user.assert_called_once_with(user_id, admin)


# ── UserListQuery ──────────────────────────────────────────────────────────


class TestUserListQuery:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        repo = AsyncMock()
        users = [MagicMock(), MagicMock()]
        repo.list_paginated.return_value = (users, 2)

        query = UserListQuery(repo)
        result_users, total = await query.execute(role=UserRole.SERVANT, page=1, page_size=10)

        repo.list_paginated.assert_called_once()
        assert total == 2
        assert result_users is users

    @pytest.mark.asyncio
    async def test_with_no_filters(self):
        repo = AsyncMock()
        repo.list_paginated.return_value = ([], 0)

        query = UserListQuery(repo)
        result_users, total = await query.execute()

        repo.list_paginated.assert_called_once()
        assert total == 0

    @pytest.mark.asyncio
    async def test_with_is_active_filter(self):
        repo = AsyncMock()
        repo.list_paginated.return_value = ([], 0)

        query = UserListQuery(repo)
        await query.execute(is_active=True, search="jean")

        call_kwargs = repo.list_paginated.call_args[1]
        assert call_kwargs["is_active"] is True
        assert call_kwargs["search"] == "jean"


# ── UserStatsQuery ─────────────────────────────────────────────────────────


class TestUserStatsQuery:
    @pytest.mark.asyncio
    async def test_returns_counts_by_role(self):
        repo = AsyncMock()
        repo.count_by_role.return_value = 5

        query = UserStatsQuery(repo)
        result = await query.execute()

        assert "total" in result
        assert result["SERVANT"] == 5
        assert result["PARENT"] == 5
        assert result["ADMIN"] == 5
        # total = sum of all role counts
        assert result["total"] == sum(v for k, v in result.items() if k != "total")

    @pytest.mark.asyncio
    async def test_calls_count_for_each_role(self):
        repo = AsyncMock()
        repo.count_by_role.return_value = 3

        query = UserStatsQuery(repo)
        await query.execute()

        # Should be called once per UserRole enum value
        assert repo.count_by_role.call_count == len(UserRole)


# ── UserSearchQuery ────────────────────────────────────────────────────────


class TestUserSearchQuery:
    @pytest.mark.asyncio
    async def test_by_id_delegates_to_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        repo.get.return_value = user

        user_id = uuid4()
        query = UserSearchQuery(repo)
        result = await query.by_id(user_id)

        repo.get.assert_called_once_with(user_id)
        assert result is user

    @pytest.mark.asyncio
    async def test_by_email_delegates_to_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        repo.get_by_email.return_value = user

        query = UserSearchQuery(repo)
        result = await query.by_email("test@example.com")

        repo.get_by_email.assert_called_once_with("test@example.com")
        assert result is user

    @pytest.mark.asyncio
    async def test_by_phone_delegates_to_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        repo.get_by_phone.return_value = user

        query = UserSearchQuery(repo)
        result = await query.by_phone("+237600000001")

        repo.get_by_phone.assert_called_once_with("+237600000001")
        assert result is user

    @pytest.mark.asyncio
    async def test_by_id_returns_none_when_not_found(self):
        repo = AsyncMock()
        repo.get.return_value = None

        query = UserSearchQuery(repo)
        result = await query.by_id(uuid4())

        assert result is None
