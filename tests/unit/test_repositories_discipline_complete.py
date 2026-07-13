"""
Unit tests for DisciplineCaseRepository - complete coverage of uncovered methods.
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


def _make_case(**kw):
    from src.core.entities.discipline import DisciplineCase, DisciplineCaseStatus, OffenseCategory, SanctionSeverity

    d = MagicMock()
    d.id = kw.get("id", uuid4())
    d.accused_user_id = kw.get("accused_user_id", uuid4())
    d.reported_by = kw.get("reported_by", uuid4())
    d.offense_category = kw.get("offense_category", OffenseCategory.INSUBORDINATION)
    d.offense_description = kw.get("offense_description", "Comportement incorrect")
    d.offense_date = kw.get("offense_date", datetime.utcnow())
    d.severity = kw.get("severity", SanctionSeverity.MINEUR)
    d.status = kw.get("status", DisciplineCaseStatus.SIGNALE)
    d.sanction_type = kw.get("sanction_type", None)
    d.verdict_notes = kw.get("verdict_notes", None)
    d.verdict_date = kw.get("verdict_date", None)
    d.verdict_by = kw.get("verdict_by", None)
    d.convocation_date = kw.get("convocation_date", None)
    d.convocation_notes = kw.get("convocation_notes", None)
    d.suspension_start = kw.get("suspension_start", None)
    d.suspension_end = kw.get("suspension_end", None)
    d.suspension_days = kw.get("suspension_days", None)
    d.created_at = kw.get("created_at", datetime.utcnow())
    d.updated_at = kw.get("updated_at", datetime.utcnow())
    return d


def _make_enc_repo(session):
    from src.infrastructure.repositories.discipline_repository import DisciplineCaseRepository

    repo = DisciplineCaseRepository(session)
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


@pytest.mark.asyncio
async def test_discipline_list_by_user():
    session = _mock_session()
    repo = _make_enc_repo(session)
    cases = [_make_case(), _make_case()]
    session.exec = AsyncMock(return_value=_exec_result(all_=cases))

    result = await repo.list_by_user(uuid4())
    assert len(result) == 2
    repo._decrypt_list.assert_called_once_with(cases)


@pytest.mark.asyncio
async def test_discipline_count_sanctions_by_user():
    from src.core.entities.discipline import SanctionType

    session = _mock_session()
    repo = _make_enc_repo(session)
    # Each sanction type (excluding AUCUNE) gets a count call
    session.exec = AsyncMock(return_value=_exec_result(one=2))

    result = await repo.count_sanctions_by_user(uuid4())
    assert isinstance(result, dict)
    # Verify AUCUNE is excluded
    assert "AUCUNE" not in result


@pytest.mark.asyncio
async def test_discipline_count_active_cases():
    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(one=3))

    result = await repo.count_active_cases(uuid4())
    assert result == 3


@pytest.mark.asyncio
async def test_discipline_enrich_case_all_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    case = _make_case(verdict_by=uuid4())

    accused = MagicMock()
    accused.first_name = "Jean"
    accused.last_name = "Doe"

    reporter = MagicMock()
    reporter.first_name = "Admin"
    reporter.last_name = "Resp"

    verdict_user = MagicMock()
    verdict_user.first_name = "Chef"
    verdict_user.last_name = "Responsable"

    session.exec = AsyncMock(side_effect=[
        _exec_result(first=accused),
        _exec_result(first=reporter),
        _exec_result(first=verdict_user),
    ])

    with patch("src.infrastructure.repositories.discipline_repository.decrypt_str_fields"):
        result = await repo.enrich_case(case)

    assert result["accused_first_name"] == "Jean"
    assert result["reporter_first_name"] == "Admin"
    assert result["verdict_by_name"] == "Chef Responsable"


@pytest.mark.asyncio
async def test_discipline_enrich_case_no_users():
    session = _mock_session()
    repo = _make_enc_repo(session)
    case = _make_case(verdict_by=None)

    session.exec = AsyncMock(side_effect=[
        _exec_result(first=None),  # accused
        _exec_result(first=None),  # reporter
        # verdict_by is None, so no 3rd call
    ])

    result = await repo.enrich_case(case)
    assert result["accused_first_name"] is None
    assert result["reporter_first_name"] is None
    assert result["verdict_by_name"] is None


@pytest.mark.asyncio
async def test_discipline_create():
    session = _mock_session()
    repo = _make_enc_repo(session)
    case = _make_case()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.create(case)
    assert result is case
    repo._encrypt_model.assert_called_once_with(case)
    repo._decrypt_model.assert_called_once_with(case)
    session.expunge.assert_called_once_with(case)


@pytest.mark.asyncio
async def test_discipline_update():
    session = _mock_session()
    repo = _make_enc_repo(session)
    case = _make_case()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.update(case)
    assert result is case
    repo._encrypt_model.assert_called_once_with(case)
    repo._decrypt_model.assert_called_once_with(case)


@pytest.mark.asyncio
async def test_discipline_delete_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    case = _make_case()

    # get() calls exec
    session.exec = AsyncMock(return_value=_exec_result(first=case))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(case.id)
    assert result is True
    session.delete.assert_called_once_with(case)


@pytest.mark.asyncio
async def test_discipline_delete_not_found():
    session = _mock_session()
    repo = _make_enc_repo(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False
