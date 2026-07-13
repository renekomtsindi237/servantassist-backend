"""
Unit tests for PosteActionRepository - uncovered methods.
(NominationRepository and AttachmentRepository are covered elsewhere.)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _exec_result(first=None, all_=None, one=None):
    r = MagicMock()
    r.first = MagicMock(return_value=first)
    r.all = MagicMock(return_value=all_ if all_ is not None else [])
    r.one = MagicMock(return_value=one if one is not None else 0)
    return r


def _make_action(**kw):
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteResponsable

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.poste = kw.get("poste", PosteResponsable.DELEGUE)
    a.category = kw.get("category", ActionCategory.DECISION)
    a.title = kw.get("title", "Action test")
    a.content = kw.get("content", None)
    a.status = kw.get("status", ActionStatus.BROUILLON)
    a.created_by = kw.get("created_by", uuid4())
    a.target_user_id = kw.get("target_user_id", None)
    a.target_event_id = kw.get("target_event_id", None)
    a.amount = kw.get("amount", None)
    a.action_date = kw.get("action_date", None)
    a.extra_data = kw.get("extra_data", None)
    a.created_at = kw.get("created_at", datetime.utcnow())
    a.updated_at = kw.get("updated_at", datetime.utcnow())
    return a


# ─────────────────────────────────────────────────────────────────────────────
#  list_all
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_list_all():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    actions = [_make_action(), _make_action()]
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=2),
        _exec_result(all_=actions),
    ])

    result = await repo.list_with_filters()
    assert result["total"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_poste_action_list_all_with_filters():
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=0),
        _exec_result(all_=[]),
    ])

    result = await repo.list_with_filters(
        poste=PosteResponsable.DELEGUE,
        category=ActionCategory.DECISION,
        status=ActionStatus.PUBLIE,
    )
    assert result["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
#  list_by_visibility
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_list_by_visibility():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    actions = [_make_action()]
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=1),
        _exec_result(all_=actions),
    ])

    result = await repo.list_by_visibility(uuid4())
    assert result["total"] == 1
    assert len(result["items"]) == 1


@pytest.mark.asyncio
async def test_poste_action_list_by_visibility_with_filters():
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=0),
        _exec_result(all_=[]),
    ])

    result = await repo.list_by_visibility(
        uuid4(),
        poste=PosteResponsable.DELEGUE,
        category=ActionCategory.RAPPORT,
        status=ActionStatus.EN_COURS,
    )
    assert result["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
#  list_by_user
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_list_by_user():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    actions = [_make_action()]
    session.exec = AsyncMock(return_value=_exec_result(all_=actions))

    result = await repo.list_by_user(uuid4())
    assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  count_by_poste_and_status
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_count_by_poste_and_status():
    from src.core.entities.responsable import ActionStatus, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    # One call per ActionStatus member
    n_statuses = len(list(ActionStatus))
    session.exec = AsyncMock(return_value=_exec_result(one=1))

    result = await repo.count_by_poste_and_status(PosteResponsable.DELEGUE)
    assert isinstance(result, dict)
    assert len(result) == n_statuses


# ─────────────────────────────────────────────────────────────────────────────
#  get_recent_by_poste
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_get_recent_by_poste():
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    actions = [_make_action(), _make_action()]
    session.exec = AsyncMock(return_value=_exec_result(all_=actions))

    result = await repo.get_recent_by_poste(PosteResponsable.DELEGUE, limit=5)
    assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
#  enrich_action
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_enrich_minimal():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    action = _make_action(target_user_id=None, target_event_id=None)

    author = MagicMock()
    author.first_name = "Jean"
    author.last_name = "D."
    session.exec = AsyncMock(return_value=_exec_result(first=author))

    with patch("src.infrastructure.repositories.responsable_repository.decrypt_str_fields"):
        result = await repo.enrich_action(action)

    assert result["author_first_name"] == "Jean"
    assert result["target_user_name"] is None
    assert result["target_event_title"] is None


@pytest.mark.asyncio
async def test_poste_action_enrich_with_target_user_and_event():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    action = _make_action(target_user_id=uuid4(), target_event_id=uuid4())

    author = MagicMock(); author.first_name = "Jean"; author.last_name = "D."
    target_user = MagicMock(); target_user.first_name = "Marc"; target_user.last_name = "T."
    target_event = MagicMock(); target_event.title = "Messe du dimanche"

    session.exec = AsyncMock(side_effect=[
        _exec_result(first=author),       # author
        _exec_result(first=target_user),  # target_user
        _exec_result(first=target_event), # target_event
    ])

    with patch("src.infrastructure.repositories.responsable_repository.decrypt_str_fields"):
        result = await repo.enrich_action(action)

    assert result["target_user_name"] == "Marc T."
    assert result["target_event_title"] == "Messe du dimanche"


@pytest.mark.asyncio
async def test_poste_action_enrich_no_author():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    action = _make_action(target_user_id=None, target_event_id=None)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.enrich_action(action)
    assert result["author_first_name"] is None


# ─────────────────────────────────────────────────────────────────────────────
#  create / update / delete
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poste_action_create():
    from src.core.entities.responsable import ActionCategory, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(
        poste=PosteResponsable.DELEGUE,
        category=ActionCategory.DECISION,
        title="Test action",
        content="some content",
        created_by=uuid4(),
    )
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_poste_action_update_found():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    action = _make_action()
    session.exec = AsyncMock(side_effect=[
        _exec_result(first=action),   # get
        _exec_result(first=action),   # refresh after commit (not called via exec)
    ])
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(action.id, {"title": "Updated title"})
    assert result is action
    assert action.title == "Updated title"


@pytest.mark.asyncio
async def test_poste_action_update_not_found():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.update(uuid4(), {"title": "No match"})
    assert result is None


@pytest.mark.asyncio
async def test_poste_action_delete_found():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    action = _make_action()
    session.exec = AsyncMock(return_value=_exec_result(first=action))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(action.id)
    assert result is True


@pytest.mark.asyncio
async def test_poste_action_delete_not_found():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False
