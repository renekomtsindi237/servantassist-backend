"""
Unit tests for UserRepository.
Uses patched encryption/decryption to avoid real key operations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _exec_result(first=None, all_=None, one=None):
    """SQLModel session.exec() result."""
    r = MagicMock()
    r.first = MagicMock(return_value=first)
    r.all = MagicMock(return_value=all_ if all_ is not None else [])
    r.one = MagicMock(return_value=one if one is not None else 0)
    return r


def _make_repo(session):
    from src.infrastructure.repositories.user_repository import UserRepository

    repo = UserRepository(session)
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


def _make_user(**kw):
    from src.core.entities.user import User, UserRole

    u = MagicMock()
    u.id = kw.get("id", uuid4())
    u.role = kw.get("role", UserRole.SERVANT)
    u.first_name = kw.get("first_name", "Jean")
    u.last_name = kw.get("last_name", "Dupont")
    u.email = kw.get("email", "jean@example.com")
    u.email_hmac = kw.get("email_hmac", "hmac_email")
    u.phone_number = kw.get("phone_number", "+237600000000")
    u.phone_hmac = kw.get("phone_hmac", "hmac_phone")
    u.is_active = kw.get("is_active", True)
    u.created_at = kw.get("created_at", datetime.utcnow())
    return u


# ─────────────────────────────────────────────────────────────────────────────
#  get()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_get_servant_found():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.SERVANT)
    # get() -> exec, _load_parent_ids -> exec
    session.exec = AsyncMock(side_effect=[
        _exec_result(first=user),   # get query
        _exec_result(all_=[]),       # parent_ids query
    ])

    result = await repo.get(user.id)
    assert result is user
    repo._decrypt_model.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_user_get_non_servant_found():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.PARENT)
    session.exec = AsyncMock(return_value=_exec_result(first=user))

    result = await repo.get(user.id)
    assert result is user
    repo._decrypt_model.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_user_get_not_found():
    session = _mock_session()
    repo = _make_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None
    repo._decrypt_model.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
#  get_by_email()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_get_by_email_found():
    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user()

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=user))
        result = await repo.get_by_email("jean@example.com")

    assert result is user
    repo._decrypt_model.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_user_get_by_email_not_found():
    session = _mock_session()
    repo = _make_repo(session)

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=None))
        result = await repo.get_by_email("nope@example.com")

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
#  get_by_phone()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_get_by_phone_found():
    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user()

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=user))
        result = await repo.get_by_phone("+237600000000")

    assert result is user


@pytest.mark.asyncio
async def test_user_get_by_phone_not_found():
    session = _mock_session()
    repo = _make_repo(session)

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=None))
        result = await repo.get_by_phone("+000000000")

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
#  list()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_list():
    session = _mock_session()
    repo = _make_repo(session)
    users = [_make_user(), _make_user()]
    session.exec = AsyncMock(return_value=_exec_result(all_=users))

    result = await repo.list()
    assert len(result) == 2
    repo._decrypt_list.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
#  list_paginated()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_list_paginated_no_filters():
    session = _mock_session()
    repo = _make_repo(session)
    users = [_make_user(), _make_user()]
    session.exec = AsyncMock(return_value=_exec_result(all_=users))

    result, total = await repo.list_paginated(page=1, page_size=10)
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_user_list_paginated_with_role_filter():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    users = [_make_user(role=UserRole.SERVANT)]
    session.exec = AsyncMock(return_value=_exec_result(all_=users))

    result, total = await repo.list_paginated(role=UserRole.SERVANT, page=1, page_size=5)
    assert total == 1


@pytest.mark.asyncio
async def test_user_list_paginated_with_search():
    session = _mock_session()
    repo = _make_repo(session)
    u = _make_user(first_name="Marc")
    session.exec = AsyncMock(return_value=_exec_result(all_=[u]))

    result, total = await repo.list_paginated(search="marc", page=1, page_size=10)
    assert total == 1
    assert result[0] is u


@pytest.mark.asyncio
async def test_user_list_paginated_search_no_match():
    session = _mock_session()
    repo = _make_repo(session)
    u = _make_user(first_name="Sylvie", last_name="Tabi", email="sylvie@example.com")
    session.exec = AsyncMock(return_value=_exec_result(all_=[u]))

    result, total = await repo.list_paginated(search="zzz_nomatch", page=1, page_size=10)
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_user_list_paginated_with_exclude_role():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    users = [_make_user(role=UserRole.SERVANT)]
    session.exec = AsyncMock(return_value=_exec_result(all_=users))

    result, total = await repo.list_paginated(exclude_role=UserRole.PARENT)
    assert total == 1


@pytest.mark.asyncio
async def test_user_list_paginated_with_is_active():
    session = _mock_session()
    repo = _make_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result, total = await repo.list_paginated(is_active=True)
    assert total == 0


# ─────────────────────────────────────────────────────────────────────────────
#  count_by_role()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_count_by_role():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(one=5))

    result = await repo.count_by_role(UserRole.SERVANT)
    assert result == 5


# ─────────────────────────────────────────────────────────────────────────────
#  create()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_create_servant():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.SERVANT)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()
    # _load_parent_ids called after create for SERVANT
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.create(user)
    assert result is user
    repo._encrypt_model.assert_called_once_with(user)
    repo._decrypt_model.assert_called_once_with(user)
    session.expunge.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_user_create_non_servant():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.PARENT)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.create(user)
    assert result is user
    repo._encrypt_model.assert_called_once_with(user)


# ─────────────────────────────────────────────────────────────────────────────
#  update()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_update_servant():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.SERVANT)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.update(user.id, user)
    assert result is user
    repo._encrypt_model.assert_called_once_with(user)
    repo._decrypt_model.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_user_update_non_servant():
    from src.core.entities.user import UserRole

    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user(role=UserRole.PARENT)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.update(user.id, user)
    assert result is user


# ─────────────────────────────────────────────────────────────────────────────
#  delete()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_delete_found():
    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user()
    session.exec = AsyncMock(return_value=_exec_result(first=user))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(user.id)
    assert result is True


@pytest.mark.asyncio
async def test_user_delete_not_found():
    session = _mock_session()
    repo = _make_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
#  email_exists() / phone_exists()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_email_exists_true():
    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user()

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=user))
        result = await repo.email_exists("jean@example.com")

    assert result is True


@pytest.mark.asyncio
async def test_user_email_exists_false():
    session = _mock_session()
    repo = _make_repo(session)

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=None))
        result = await repo.email_exists("nope@example.com")

    assert result is False


@pytest.mark.asyncio
async def test_user_email_exists_with_exclude_id():
    session = _mock_session()
    repo = _make_repo(session)

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=None))
        result = await repo.email_exists("jean@example.com", exclude_id=uuid4())

    assert result is False


@pytest.mark.asyncio
async def test_user_phone_exists_true():
    session = _mock_session()
    repo = _make_repo(session)
    user = _make_user()

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=user))
        result = await repo.phone_exists("+237600000000")

    assert result is True


@pytest.mark.asyncio
async def test_user_phone_exists_with_exclude_id():
    session = _mock_session()
    repo = _make_repo(session)

    with patch("src.infrastructure.repositories.user_repository.get_encryptor") as mock_enc:
        mock_enc.return_value.hmac_index.return_value = "hmac"
        session.exec = AsyncMock(return_value=_exec_result(first=None))
        result = await repo.phone_exists("+000", exclude_id=uuid4())

    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
#  get_parents_of() / get_children_of()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_get_parents_of():
    session = _mock_session()
    repo = _make_repo(session)
    parent = _make_user()
    session.exec = AsyncMock(return_value=_exec_result(all_=[parent]))

    result = await repo.get_parents_of(uuid4())
    assert len(result) == 1
    repo._decrypt_list.assert_called()


@pytest.mark.asyncio
async def test_user_get_children_of():
    session = _mock_session()
    repo = _make_repo(session)
    child = _make_user()
    session.exec = AsyncMock(return_value=_exec_result(all_=[child]))

    result = await repo.get_children_of(uuid4())
    assert len(result) == 1
    repo._decrypt_list.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
#  add_parent_link()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_add_parent_link_success():
    session = _mock_session()
    repo = _make_repo(session)
    # Fewer than 3 parents currently
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))
    session.add = MagicMock()
    session.commit = AsyncMock()

    servant_id = uuid4()
    parent_id = uuid4()
    await repo.add_parent_link(servant_id, parent_id)
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_add_parent_link_already_exists():
    """Should be idempotent — no add when parent already linked."""
    session = _mock_session()
    repo = _make_repo(session)
    parent_id = uuid4()
    parent = _make_user(id=parent_id)
    session.exec = AsyncMock(return_value=_exec_result(all_=[parent]))
    session.add = MagicMock()
    session.commit = AsyncMock()

    await repo.add_parent_link(uuid4(), parent_id)
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_user_add_parent_link_max_exceeded():
    from fastapi import HTTPException

    session = _mock_session()
    repo = _make_repo(session)
    parents = [_make_user(), _make_user(), _make_user()]  # 3 existing parents
    session.exec = AsyncMock(return_value=_exec_result(all_=parents))

    with pytest.raises(HTTPException) as exc:
        await repo.add_parent_link(uuid4(), uuid4())
    assert exc.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
#  remove_parent_link()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_remove_parent_link_found():
    session = _mock_session()
    repo = _make_repo(session)
    link = MagicMock()
    session.exec = AsyncMock(return_value=_exec_result(first=link))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    await repo.remove_parent_link(uuid4(), uuid4())
    session.delete.assert_called_once_with(link)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_remove_parent_link_not_found():
    session = _mock_session()
    repo = _make_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))
    session.delete = AsyncMock()

    await repo.remove_parent_link(uuid4(), uuid4())
    session.delete.assert_not_called()
