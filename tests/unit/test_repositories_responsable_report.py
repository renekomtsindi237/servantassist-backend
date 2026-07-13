"""
Unit tests for NominationRepository, PosteActionRepository, and ReportRepository.
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


def _sa_exec_result(scalar_one=None, scalars_list=None):
    """SQLAlchemy execute() result (not session.exec())."""
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    return r


# ═══════════════════════════════════════════════════════════════════════════════
#  NominationRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_nomination(**kw):
    from src.core.entities.responsable import Nomination, NominationStatus, PosteResponsable

    n = MagicMock()
    n.id = kw.get("id", uuid4())
    n.user_id = kw.get("user_id", uuid4())
    n.poste = kw.get("poste", PosteResponsable.DELEGUE)
    n.status = kw.get("status", NominationStatus.ACTIVE)
    n.nominated_by = kw.get("nominated_by", uuid4())
    n.notes = kw.get("notes", None)
    n.nominated_at = kw.get("nominated_at", datetime.utcnow())
    n.revoked_at = kw.get("revoked_at", None)
    n.revoked_by = kw.get("revoked_by", None)
    return n


@pytest.mark.asyncio
async def test_nomination_get_found():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination()
    session.exec = AsyncMock(return_value=_exec_result(first=n))

    result = await repo.get(n.id)
    assert result is n


@pytest.mark.asyncio
async def test_nomination_get_not_found():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_nomination_get_active_by_poste():
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination()
    session.exec = AsyncMock(return_value=_exec_result(first=n))

    result = await repo.get_active_by_poste(PosteResponsable.CONSEILLER)
    assert result is n


@pytest.mark.asyncio
async def test_nomination_get_active_by_user():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    nominations = [_make_nomination()]
    session.exec = AsyncMock(return_value=_exec_result(all_=nominations))

    result = await repo.get_active_by_user(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_nomination_get_active_by_user_and_poste():
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination()
    session.exec = AsyncMock(return_value=_exec_result(first=n))

    result = await repo.get_active_by_user_and_poste(n.user_id, PosteResponsable.CONSEILLER)
    assert result is n


@pytest.mark.asyncio
async def test_nomination_list_all_active():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    nominations = [_make_nomination(), _make_nomination()]
    session.exec = AsyncMock(return_value=_exec_result(all_=nominations))

    result = await repo.list_all_active()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_nomination_list_history():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    nominations = [_make_nomination()]
    session.exec = AsyncMock(return_value=_exec_result(all_=nominations))

    result = await repo.list_history()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_nomination_list_history_with_filters():
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.list_history(user_id=uuid4(), poste=PosteResponsable.CONSEILLER)
    assert result == []


@pytest.mark.asyncio
async def test_nomination_enrich_nomination():
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination(poste=PosteResponsable.CONSEILLER)

    user = MagicMock()
    user.first_name = "Pierre"
    user.last_name = "Durand"
    user.email = "pierre@example.com"
    user.phone_number = "+237"
    session.exec = AsyncMock(return_value=_exec_result(first=user))

    with patch("src.infrastructure.repositories.responsable_repository.decrypt_str_fields"):
        result = await repo.enrich_nomination(n)

    assert result["user_first_name"] == "Pierre"
    assert "poste" in result


@pytest.mark.asyncio
async def test_nomination_create():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(n)
    assert result is n


@pytest.mark.asyncio
async def test_nomination_update():
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    session = _mock_session()
    repo = NominationRepository(session)
    n = _make_nomination()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(n)
    assert result is n


# ─── PosteActionRepository ────────────────────────────────────────────────────


def _make_poste_action(**kw):
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteAction, PosteResponsable

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.poste = kw.get("poste", PosteResponsable.CONSEILLER)
    a.category = kw.get("category", ActionCategory.DECISION)
    a.status = kw.get("status", ActionStatus.EN_COURS)
    a.created_at = kw.get("created_at", datetime.utcnow())
    return a


@pytest.mark.asyncio
async def test_poste_action_get_found():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    a = _make_poste_action()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get(a.id)
    assert result is a


@pytest.mark.asyncio
async def test_poste_action_get_by_id():
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    a = _make_poste_action()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get_by_id(a.id)
    assert result is a


@pytest.mark.asyncio
async def test_poste_action_list_by_poste():
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    actions = [_make_poste_action()]
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=1),
        _exec_result(all_=actions),
    ])

    result, total = await repo.list_by_poste(PosteResponsable.CONSEILLER)
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_poste_action_list_by_poste_with_filters():
    from src.core.entities.responsable import ActionCategory, ActionStatus, PosteResponsable
    from src.infrastructure.repositories.responsable_repository import PosteActionRepository

    session = _mock_session()
    repo = PosteActionRepository(session)
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=0),
        _exec_result(all_=[]),
    ])

    result, total = await repo.list_by_poste(
        PosteResponsable.CONSEILLER,
        category=ActionCategory.DECISION,
        status=ActionStatus.EN_COURS,
    )
    assert total == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  ReportRepository (uses SQLAlchemy AsyncSession.execute(), not session.exec())
# ═══════════════════════════════════════════════════════════════════════════════


def _make_report(**kw):
    from src.core.entities.report import Report, ReportStatus, ReportType

    r = MagicMock()
    r.id = kw.get("id", uuid4())
    r.type = kw.get("type", ReportType.MEETING)
    r.status = kw.get("status", ReportStatus.DRAFT)
    r.created_by = kw.get("created_by", uuid4())
    r.created_at = kw.get("created_at", datetime.utcnow())
    r.updated_at = kw.get("updated_at", datetime.utcnow())
    r.published_at = kw.get("published_at", None)
    r.report_date = kw.get("report_date", datetime.utcnow())
    return r


@pytest.mark.asyncio
async def test_report_create():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(report)
    assert result is report


@pytest.mark.asyncio
async def test_report_get_by_id_found():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=report))

    result = await repo.get_by_id(report.id)
    assert result is report


@pytest.mark.asyncio
async def test_report_get_by_id_not_found():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_report_list_reports():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    reports = [_make_report()]
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=reports),
        _sa_exec_result(scalar_one=1),
    ])

    result, total = await repo.list_reports()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_report_list_with_filters():
    from src.core.entities.report import ReportStatus, ReportType
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=[]),
        _sa_exec_result(scalar_one=0),
    ])

    result, total = await repo.list_reports(
        report_type=ReportType.MEETING,
        status=ReportStatus.DRAFT,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_report_update():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(report)
    assert result is report


@pytest.mark.asyncio
async def test_report_delete_found():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=report))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(report.id)
    assert result is True


@pytest.mark.asyncio
async def test_report_delete_not_found():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_report_publish_found():
    from src.core.entities.report import ReportStatus
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=report))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.publish(report.id)
    assert result is report
    assert report.status == ReportStatus.PUBLISHED


@pytest.mark.asyncio
async def test_report_publish_not_found():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.publish(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_report_archive_found():
    from src.core.entities.report import ReportStatus
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    report = _make_report()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=report))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.archive(report.id)
    assert result is report
    assert report.status == ReportStatus.ARCHIVED


@pytest.mark.asyncio
async def test_report_get_by_created_by():
    from src.infrastructure.repositories.report_repository import ReportRepository

    session = _mock_session()
    repo = ReportRepository(session)
    reports = [_make_report()]
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=reports),
        _sa_exec_result(scalar_one=1),
    ])

    result, total = await repo.get_by_created_by(uuid4())
    assert len(result) == 1
    assert total == 1


# ─── AttachmentRepository ─────────────────────────────────────────────────────


def _make_attachment(**kw):
    from src.core.entities.report import ReportAttachment

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.report_id = kw.get("report_id", uuid4())
    a.filename = kw.get("filename", "test.pdf")
    a.created_at = kw.get("created_at", datetime.utcnow())
    return a


@pytest.mark.asyncio
async def test_attachment_create():
    from src.infrastructure.repositories.report_repository import AttachmentRepository

    session = _mock_session()
    repo = AttachmentRepository(session)
    att = _make_attachment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(att)
    assert result is att


@pytest.mark.asyncio
async def test_attachment_get_by_id_found():
    from src.infrastructure.repositories.report_repository import AttachmentRepository

    session = _mock_session()
    repo = AttachmentRepository(session)
    att = _make_attachment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=att))

    result = await repo.get_by_id(att.id)
    assert result is att


@pytest.mark.asyncio
async def test_attachment_get_by_report():
    from src.infrastructure.repositories.report_repository import AttachmentRepository

    session = _mock_session()
    repo = AttachmentRepository(session)
    atts = [_make_attachment(), _make_attachment()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=atts))

    result = await repo.get_by_report(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_attachment_delete_found():
    from src.infrastructure.repositories.report_repository import AttachmentRepository

    session = _mock_session()
    repo = AttachmentRepository(session)
    att = _make_attachment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=att))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(att.id)
    assert result is True


@pytest.mark.asyncio
async def test_attachment_delete_not_found():
    from src.infrastructure.repositories.report_repository import AttachmentRepository

    session = _mock_session()
    repo = AttachmentRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False
