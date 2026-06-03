"""Unit tests for ApiKeyService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from src.application.services.api_key_service import ApiKeyService
from src.core.entities.api_key import ApiKey


def _make_key(user_id=None, is_active=True, **kw) -> ApiKey:
    return ApiKey(
        id=kw.pop("id", uuid4()),
        name=kw.pop("name", "Test Key"),
        key_hash=kw.pop("key_hash", "$2b$12$fakehash"),
        user_id=user_id or uuid4(),
        scopes=kw.pop("scopes", []),
        is_active=is_active,
        **kw,
    )


def _svc(repo=None) -> ApiKeyService:
    return ApiKeyService(repo or AsyncMock())


# ─── _generate_raw_key ────────────────────────────────────────────────────────


def test_generate_raw_key_starts_with_prefix():
    svc = _svc()
    key = svc._generate_raw_key()
    assert key.startswith("sa_")
    assert len(key) > 10


def test_generate_raw_key_unique():
    svc = _svc()
    assert svc._generate_raw_key() != svc._generate_raw_key()


# ─── create_key ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_key_success():
    user_id = uuid4()
    saved = _make_key(user_id=user_id)
    repo = AsyncMock()
    repo.create.return_value = saved

    with patch("src.application.services.api_key_service.SecurityUtils.get_password_hash", return_value="hashed"):
        api_key, raw = await _svc(repo).create_key(user_id, "My Key", scopes=["read"])

    assert api_key.id == saved.id
    assert raw.startswith("sa_")
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_key_no_scopes():
    user_id = uuid4()
    saved = _make_key(user_id=user_id, scopes=[])
    repo = AsyncMock()
    repo.create.return_value = saved

    with patch("src.application.services.api_key_service.SecurityUtils.get_password_hash", return_value="hashed"):
        api_key, raw = await _svc(repo).create_key(user_id, "Key")

    assert api_key.scopes == []


# ─── verify_key ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_key_wrong_prefix():
    result = await _svc().verify_key("wrong_prefix_key")
    assert result is None


@pytest.mark.asyncio
async def test_verify_key_no_matching_hash():
    repo = AsyncMock()
    repo.list_all.return_value = [_make_key(key_hash="$hash")]

    with patch("src.application.services.api_key_service.SecurityUtils.verify_password", return_value=False):
        result = await _svc(repo).verify_key("sa_testkey")

    assert result is None


@pytest.mark.asyncio
async def test_verify_key_inactive_skipped():
    inactive_key = _make_key(is_active=False)
    repo = AsyncMock()
    repo.list_all.return_value = [inactive_key]

    result = await _svc(repo).verify_key("sa_testkey")
    assert result is None


@pytest.mark.asyncio
async def test_verify_key_success():
    key = _make_key()
    repo = AsyncMock()
    repo.list_all.return_value = [key]
    repo.touch = AsyncMock()

    with patch("src.application.services.api_key_service.SecurityUtils.verify_password", return_value=True):
        result = await _svc(repo).verify_key("sa_validkey")

    assert result.id == key.id
    repo.touch.assert_called_once_with(key.id)


# ─── list_user_keys ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_user_keys():
    user_id = uuid4()
    keys = [_make_key(user_id=user_id), _make_key(user_id=user_id)]
    repo = AsyncMock()
    repo.get_by_user.return_value = keys
    result = await _svc(repo).list_user_keys(user_id)
    assert len(result) == 2


# ─── list_all_keys ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_all_keys():
    keys = [_make_key(), _make_key()]
    repo = AsyncMock()
    repo.list_all.return_value = keys
    result = await _svc(repo).list_all_keys()
    assert len(result) == 2
    repo.list_all.assert_called_once_with(limit=50, offset=0)


# ─── revoke_key ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_key_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(repo).revoke_key(uuid4(), uuid4(), is_admin=True)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_key_forbidden_non_owner():
    key = _make_key(user_id=uuid4())
    repo = AsyncMock()
    repo.get_by_id.return_value = key
    with pytest.raises(HTTPException) as e:
        await _svc(repo).revoke_key(key.id, uuid4(), is_admin=False)
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_revoke_key_owner_success():
    user_id = uuid4()
    key = _make_key(user_id=user_id)
    revoked = _make_key(id=key.id, user_id=user_id, is_active=False)
    repo = AsyncMock()
    repo.get_by_id.return_value = key
    repo.revoke.return_value = revoked
    result = await _svc(repo).revoke_key(key.id, user_id, is_admin=False)
    assert result.id == key.id


@pytest.mark.asyncio
async def test_revoke_key_admin_success():
    key = _make_key(user_id=uuid4())
    revoked = _make_key(id=key.id, is_active=False)
    repo = AsyncMock()
    repo.get_by_id.return_value = key
    repo.revoke.return_value = revoked
    result = await _svc(repo).revoke_key(key.id, uuid4(), is_admin=True)
    assert result.id == key.id


# ─── delete_key ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_key_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(repo).delete_key(uuid4(), uuid4(), is_admin=True)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_key_forbidden():
    key = _make_key(user_id=uuid4())
    repo = AsyncMock()
    repo.get_by_id.return_value = key
    with pytest.raises(HTTPException) as e:
        await _svc(repo).delete_key(key.id, uuid4(), is_admin=False)
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_key_success():
    user_id = uuid4()
    key = _make_key(user_id=user_id)
    repo = AsyncMock()
    repo.get_by_id.return_value = key
    repo.delete = AsyncMock()
    await _svc(repo).delete_key(key.id, user_id, is_admin=False)
    repo.delete.assert_called_once_with(key.id)
