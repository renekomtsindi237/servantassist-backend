"""
Unit tests for InvitationCodeRepository - missing methods (update, mark_as_used, revoke).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _exec_result(first=None, all_=None):
    r = MagicMock()
    r.first = MagicMock(return_value=first)
    r.all = MagicMock(return_value=all_ if all_ is not None else [])
    return r


def _make_enc_repo(session):
    from src.infrastructure.repositories.invitation_repository import InvitationCodeRepository

    repo = InvitationCodeRepository(session)
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


def _make_invitation(**kw):
    from src.core.entities.invitation import InvitationCode, InvitationStatus

    inv = MagicMock()
    inv.id = kw.get("id", uuid4())
    inv.code = kw.get("code", "INV-123456")
    inv.status = kw.get("status", InvitationStatus.PENDING)
    inv.created_by = kw.get("created_by", uuid4())
    inv.expires_at = kw.get("expires_at", None)
    inv.used_by = kw.get("used_by", None)
    inv.used_at = kw.get("used_at", None)
    return inv


@pytest.mark.asyncio
async def test_invitation_update():
    """update() encrypts then fetches updated invitation."""
    from src.core.entities.invitation import InvitationStatus

    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation()
    inv_updated = _make_invitation(id=inv.id, status=InvitationStatus.ACCEPTED)

    session.merge = AsyncMock()
    session.commit = AsyncMock()
    # get_by_id() after merge calls exec
    session.exec = AsyncMock(return_value=_exec_result(first=inv_updated))

    result = await repo.update(inv.id, inv)
    repo._encrypt_model.assert_called_once_with(inv)
    repo._decrypt_model.assert_called()


@pytest.mark.asyncio
async def test_invitation_mark_as_used_code_not_found():
    """mark_as_used returns None if code is not found."""
    session = _mock_session()
    repo = _make_enc_repo(session)
    # get_by_code returns None
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.mark_as_used("NOTFOUND", uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_invitation_mark_as_used_success():
    """mark_as_used updates status and calls update()."""
    from src.core.entities.invitation import InvitationStatus

    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation(status=InvitationStatus.PENDING)
    user_id = uuid4()

    # First exec for get_by_code; second for get_by_id inside update
    inv_updated = _make_invitation(id=inv.id, status=InvitationStatus.ACCEPTED)
    session.exec = AsyncMock(side_effect=[
        _exec_result(first=inv),          # get_by_code
        _exec_result(first=inv_updated),  # get_by_id inside update
    ])
    session.merge = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.mark_as_used(inv.code, user_id)
    assert inv.status == InvitationStatus.ACCEPTED
    assert inv.used_by == user_id


@pytest.mark.asyncio
async def test_invitation_revoke_not_found():
    """revoke returns None if invitation not found."""
    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.revoke(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_invitation_revoke_success():
    """revoke sets status to REVOKED and calls update."""
    from src.core.entities.invitation import InvitationStatus

    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation(status=InvitationStatus.PENDING)
    inv_revoked = _make_invitation(id=inv.id, status=InvitationStatus.REVOKED)

    session.exec = AsyncMock(side_effect=[
        _exec_result(first=inv),          # get_by_id (first call in revoke)
        _exec_result(first=inv_revoked),  # get_by_id inside update
    ])
    session.merge = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.revoke(inv.id)
    assert inv.status == InvitationStatus.REVOKED
