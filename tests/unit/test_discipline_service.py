"""
Unit tests for DisciplineService (CENSEUR).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from fastapi import HTTPException

from src.application.services.discipline_service import DisciplineService
from src.core.entities.discipline import (
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.discipline import DisciplineCaseCreate, DisciplineVerdict


@pytest.fixture
def mock_case_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_attendance_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_case_repo, mock_user_repo, mock_attendance_repo):
    return DisciplineService(mock_case_repo, mock_user_repo, mock_attendance_repo)


@pytest.fixture
def sample_servant():
    return User(
        id=uuid4(),
        email="servant@test.com",
        first_name="Jean",
        last_name="Dupont",
        role=UserRole.SERVANT,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_open_case_success(service, mock_case_repo, mock_user_repo, sample_servant):
    mock_user_repo.get.return_value = sample_servant

    case = DisciplineCase(
        id=uuid4(),
        accused_user_id=sample_servant.id,
        reported_by=uuid4(),
        offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
        offense_description="Absent sans raison",
        status=DisciplineCaseStatus.SIGNALE,
    )
    mock_case_repo.create.return_value = case
    mock_case_repo.enrich_case.return_value = {
        **case.model_dump(),
        "accused_name": "Jean Dupont",
        "reporter_name": "Marie Martin",
    }

    data = DisciplineCaseCreate(
        accused_user_id=sample_servant.id,
        offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
        offense_description="Absent sans raison",
    )

    result = await service.open_case(data, uuid4())

    assert result.accused_user_id == sample_servant.id
    assert result.status == DisciplineCaseStatus.SIGNALE
    mock_case_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_render_verdict_success(service, mock_case_repo):
    case_id = uuid4()
    case = DisciplineCase(
        id=case_id,
        accused_user_id=uuid4(),
        reported_by=uuid4(),
        offense_category=OffenseCategory.INSUBORDINATION,
        offense_description="Manque de respect",
        status=DisciplineCaseStatus.EN_AUDIENCE,
    )

    async def side_effect_update(obj):
        return obj

    async def side_effect_enrich(obj):
        return {**obj.model_dump(), "accused_name": "Test", "reporter_name": "Test"}

    mock_case_repo.get.return_value = case
    mock_case_repo.update.side_effect = side_effect_update
    mock_case_repo.enrich_case.side_effect = side_effect_enrich

    data = DisciplineVerdict(
        sanction_type=SanctionType.AVERTISSEMENT_ECRIT,
        verdict_notes="Avertissement car premiere fois",
    )

    result = await service.render_verdict(case_id, data, uuid4())

    assert result.status == DisciplineCaseStatus.VERDICT_RENDU
    assert result.sanction_type == SanctionType.AVERTISSEMENT_ECRIT
    mock_case_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_execute_sanction_exclusion(service, mock_case_repo, mock_user_repo):
    case_id = uuid4()
    accused_id = uuid4()
    case = DisciplineCase(
        id=case_id,
        accused_user_id=accused_id,
        reported_by=uuid4(),
        offense_category=OffenseCategory.BAGARRE_VIOLENCE,
        offense_description="Tres grave",
        status=DisciplineCaseStatus.VERDICT_RENDU,
        sanction_type=SanctionType.EXCLUSION_DEFINITIVE,
    )

    user = User(
        id=accused_id,
        email="test@test.com",
        first_name="Exclu",
        last_name="User",
        role=UserRole.SERVANT,
        is_active=True,
    )

    async def side_effect_update(obj):
        return obj

    async def side_effect_enrich(obj):
        return {**obj.model_dump()}

    mock_case_repo.get.return_value = case
    mock_case_repo.update.side_effect = side_effect_update
    mock_case_repo.enrich_case.side_effect = side_effect_enrich
    mock_user_repo.get.return_value = user

    result = await service.execute_sanction(case_id)

    assert result.status == DisciplineCaseStatus.EXECUTE
    mock_user_repo.update.assert_called_once()
    assert user.is_active is False
