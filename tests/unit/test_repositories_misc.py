"""
Unit tests for remaining repositories with low/zero coverage:
- PasswordResetCodeRepository
- CouncilMeetingRepository
- ApiKeyRepository
- ClassementRepository
- ConnectionLogRepository (partial)
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# ─── Mock session ─────────────────────────────────────────────────────────────


def _mock_session() -> AsyncMock:
    return AsyncMock()


def _exec_result(first=None, all_=None, scalar_one=None):
    """Build mock result for session.exec()."""
    result = MagicMock()
    result.first = MagicMock(return_value=first)
    result.all = MagicMock(return_value=all_ if all_ is not None else [])
    result.scalar_one_or_none = MagicMock(return_value=scalar_one)
    result.scalar_one = MagicMock(return_value=scalar_one)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  PasswordResetCodeRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_reset_code(**kw):
    from src.core.entities.password_reset_code import PasswordResetCode

    return PasswordResetCode(
        id=kw.pop("id", uuid4()),
        email=kw.pop("email", "test@example.com"),
        code=kw.pop("code", "123456"),
        expires_at=kw.pop("expires_at", datetime.utcnow() + timedelta(minutes=10)),
        used=kw.pop("used", False),
        **kw,
    )


@pytest.mark.asyncio
async def test_password_reset_code_create():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)
    code = _make_reset_code()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(code)
    session.add.assert_called_once_with(code)
    session.commit.assert_called_once()
    assert result is code


@pytest.mark.asyncio
async def test_password_reset_code_get_valid_found():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)
    code = _make_reset_code()

    session.exec = AsyncMock(return_value=_exec_result(first=code))

    result = await repo.get_valid("test@example.com", "123456")
    assert result is code


@pytest.mark.asyncio
async def test_password_reset_code_get_valid_not_found():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get_valid("test@example.com", "999999")
    assert result is None


@pytest.mark.asyncio
async def test_password_reset_code_mark_used_found():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)
    code = _make_reset_code(used=False)

    session.exec = AsyncMock(return_value=_exec_result(first=code))
    session.add = MagicMock()
    session.commit = AsyncMock()

    await repo.mark_used(code.id)

    assert code.used is True
    session.add.assert_called_once_with(code)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_password_reset_code_mark_used_not_found():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))
    session.add = MagicMock()
    session.commit = AsyncMock()

    await repo.mark_used(uuid4())
    # No add/commit when not found
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_password_reset_code_delete_expired():
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)

    session.exec = AsyncMock(return_value=_exec_result())
    session.commit = AsyncMock()

    await repo.delete_expired()
    session.exec.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_password_reset_code_delete_for_user():
    from uuid import uuid4

    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    session = _mock_session()
    repo = PasswordResetCodeRepository(session)

    session.exec = AsyncMock(return_value=_exec_result())
    session.commit = AsyncMock()

    await repo.delete_for_user(uuid4())
    session.exec.assert_called_once()
    session.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
#  CouncilMeetingRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_council_meeting(**kw):
    from src.core.entities.council_meeting import CouncilMeeting

    return CouncilMeeting(
        id=kw.pop("id", uuid4()),
        title=kw.pop("title", "Meeting Test"),
        meeting_date=kw.pop("meeting_date", datetime.utcnow()),
        created_by=kw.pop("created_by", uuid4()),
        **kw,
    )


def _make_council_attendance(**kw):
    from src.core.entities.council_meeting import CouncilAttendance

    return CouncilAttendance(
        id=kw.pop("id", uuid4()),
        meeting_id=kw.pop("meeting_id", uuid4()),
        responsable_id=kw.pop("responsable_id", uuid4()),
        was_present=kw.pop("was_present", True),
        **kw,
    )


@pytest.mark.asyncio
async def test_council_meeting_create():
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)
    meeting = _make_council_meeting()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_meeting(meeting)
    session.add.assert_called_once_with(meeting)
    assert result is meeting


@pytest.mark.asyncio
async def test_council_meeting_get_found():
    from src.core.entities.council_meeting import CouncilMeeting
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)
    meeting = _make_council_meeting()

    session.get = AsyncMock(return_value=meeting)

    result = await repo.get_meeting(meeting.id)
    assert result is meeting
    session.get.assert_called_once_with(CouncilMeeting, meeting.id)


@pytest.mark.asyncio
async def test_council_meeting_get_not_found():
    from src.core.entities.council_meeting import CouncilMeeting
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)

    session.get = AsyncMock(return_value=None)
    meeting_id = uuid4()

    result = await repo.get_meeting(meeting_id)
    assert result is None


@pytest.mark.asyncio
async def test_council_meeting_add_attendance():
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)
    attendance = _make_council_attendance()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.add_attendance(attendance)
    session.add.assert_called_once_with(attendance)
    assert result is attendance


@pytest.mark.asyncio
async def test_council_meeting_get_responsable_attendances():
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)

    responsable_id = uuid4()
    attendances = [_make_council_attendance(responsable_id=responsable_id)]

    session.exec = AsyncMock(return_value=_exec_result(all_=attendances))

    result = await repo.get_responsable_attendances(responsable_id, limit=3)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_council_meeting_get_responsable_attendances_empty():
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository

    session = _mock_session()
    repo = CouncilMeetingRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.get_responsable_attendances(uuid4())
    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
#  ApiKeyRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_api_key(**kw):
    from src.core.entities.api_key import ApiKey

    return ApiKey(
        id=kw.pop("id", uuid4()),
        name=kw.pop("name", "Test Key"),
        key_hash=kw.pop("key_hash", "$2b$hash"),
        user_id=kw.pop("user_id", uuid4()),
        scopes=kw.pop("scopes", []),
        is_active=kw.pop("is_active", True),
        last_used_at=kw.pop("last_used_at", None),
        created_at=kw.pop("created_at", datetime.utcnow()),
        **kw,
    )


@pytest.mark.asyncio
async def test_api_key_create():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    key = _make_api_key()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(key)
    session.add.assert_called_once_with(key)
    assert result is key


@pytest.mark.asyncio
async def test_api_key_get_by_id_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    key = _make_api_key()

    session.exec = AsyncMock(return_value=_exec_result(first=key))

    result = await repo.get_by_id(key.id)
    assert result is key


@pytest.mark.asyncio
async def test_api_key_get_by_id_not_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_api_key_get_by_user():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    user_id = uuid4()
    keys = [_make_api_key(user_id=user_id), _make_api_key(user_id=user_id)]

    session.exec = AsyncMock(return_value=_exec_result(all_=keys))

    result = await repo.get_by_user(user_id)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_api_key_list_all():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    keys = [_make_api_key()]

    session.exec = AsyncMock(return_value=_exec_result(all_=keys))

    result = await repo.list_all(limit=50, offset=0)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_api_key_revoke_not_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.revoke(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_api_key_revoke_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    key = _make_api_key(is_active=True)

    session.exec = AsyncMock(return_value=_exec_result(first=key))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.revoke(key.id)
    assert result is key
    assert key.is_active is False


@pytest.mark.asyncio
async def test_api_key_delete_not_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_api_key_delete_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    key = _make_api_key()

    session.exec = AsyncMock(return_value=_exec_result(first=key))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(key.id)
    assert result is True
    session.delete.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_api_key_touch_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)
    key = _make_api_key(last_used_at=None)

    session.exec = AsyncMock(return_value=_exec_result(first=key))
    session.add = MagicMock()
    session.commit = AsyncMock()

    await repo.touch(key.id)
    assert key.last_used_at is not None


@pytest.mark.asyncio
async def test_api_key_touch_not_found():
    from src.infrastructure.repositories.api_key_repository import ApiKeyRepository

    session = _mock_session()
    repo = ApiKeyRepository(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))
    session.add = MagicMock()
    session.commit = AsyncMock()

    # Should not raise
    await repo.touch(uuid4())
    session.add.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
#  ClassementRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_classement(**kw):
    from src.core.entities.classement import Classement, ClassementStatus, ClassementType

    return Classement(
        id=kw.pop("id", uuid4()),
        type=kw.pop("type", ClassementType.DIMANCHE),
        status=kw.pop("status", ClassementStatus.BROUILLON),
        date=kw.pop("date", datetime.utcnow()),
        heure=kw.pop("heure", "08:00"),
        lieu=kw.pop("lieu", "Cathédrale"),
        postes=kw.pop("postes", []),
        created_by=kw.pop("created_by", uuid4()),
        created_at=kw.pop("created_at", datetime.utcnow()),
        updated_at=kw.pop("updated_at", datetime.utcnow()),
        **kw,
    )


def _exec_result_sa(scalars_list=None, scalar_one=None):
    """For SQLAlchemy AsyncSession execute() results."""
    result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    result.scalars.return_value = scalars_obj
    result.scalar_one_or_none = MagicMock(return_value=scalar_one)
    result.scalar_one = MagicMock(return_value=scalar_one)
    return result


@pytest.mark.asyncio
async def test_classement_create():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)
    cl = _make_classement()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(cl)
    session.add.assert_called_once_with(cl)
    assert result is cl


@pytest.mark.asyncio
async def test_classement_get_by_id_found():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)
    cl = _make_classement()

    session.execute = AsyncMock(return_value=_exec_result_sa(scalar_one=cl))

    result = await repo.get_by_id(cl.id)
    assert result is cl


@pytest.mark.asyncio
async def test_classement_get_by_id_not_found():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)

    session.execute = AsyncMock(return_value=_exec_result_sa(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_classement_list():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)

    items = [_make_classement(), _make_classement()]

    scalars_result = _exec_result_sa(scalars_list=items)
    count_result = _exec_result_sa(scalar_one=2)

    session.execute = AsyncMock(side_effect=[scalars_result, count_result])

    result, total = await repo.list()
    assert len(result) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_classement_list_with_filters():
    from src.core.entities.classement import ClassementStatus, ClassementType
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)

    scalars_result = _exec_result_sa(scalars_list=[])
    count_result = _exec_result_sa(scalar_one=0)

    session.execute = AsyncMock(side_effect=[scalars_result, count_result])

    result, total = await repo.list(
        type=ClassementType.DIMANCHE,
        status=ClassementStatus.PUBLIE,
    )
    assert result == []
    assert total == 0


@pytest.mark.asyncio
async def test_classement_update():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)
    cl = _make_classement()

    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(cl)
    session.commit.assert_called_once()
    assert result is cl


@pytest.mark.asyncio
async def test_classement_delete_not_found():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)

    session.execute = AsyncMock(return_value=_exec_result_sa(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_classement_delete_found():
    from src.infrastructure.repositories.classement_repository import ClassementRepository

    session = _mock_session()
    repo = ClassementRepository(session)
    cl = _make_classement()

    session.execute = AsyncMock(return_value=_exec_result_sa(scalar_one=cl))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(cl.id)
    assert result is True
    session.delete.assert_called_once_with(cl)
