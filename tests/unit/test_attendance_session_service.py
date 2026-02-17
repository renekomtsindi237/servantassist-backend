"""
Tests unitaires pour le service de gestion des appels (CENSEUR).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.application.services.attendance_session_service import AttendanceSessionService
from src.core.entities.attendance_session import AttendanceRecord, AttendanceSession, AttendanceStatus
from src.core.entities.user import User, UserRole
from src.presentation.schemas.attendance_session import (
    AttendanceRecordCreate,
    AttendanceReportRequest,
    AttendanceSessionCreate,
)


@pytest.fixture
def mock_session_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_session_repo, mock_user_repo):
    return AttendanceSessionService(mock_session_repo, mock_user_repo)


@pytest.fixture
def sample_session():
    now = datetime.now(timezone.utc)
    return AttendanceSession(
        id=uuid4(),
        session_date=now,
        session_time="07h30",
        location="Sacristie",
        conducted_by=uuid4(),
        notes="Appel du samedi",
        created_at=now,
        updated_at=now,
    )


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
async def test_create_session_success(service, mock_session_repo, sample_session):
    mock_session_repo.create_session.return_value = sample_session
    mock_session_repo.enrich_session.return_value = {
        **sample_session.model_dump(),
        "conducted_by_name": "Test User",
        "created_at": sample_session.created_at,
        "updated_at": sample_session.updated_at,
        "records": [],
        "total_servants": 0,
        "present_count": 0,
        "absent_count": 0,
        "late_count": 0,
        "excused_count": 0,
    }

    data = AttendanceSessionCreate(
        session_date=sample_session.session_date,
        session_time=sample_session.session_time,
        location=sample_session.location,
        notes=sample_session.notes,
    )

    result = await service.create_session(data, sample_session.conducted_by)

    assert result.session_date == sample_session.session_date
    mock_session_repo.create_session.assert_called_once()


@pytest.mark.asyncio
async def test_mark_attendance_success(
    service, mock_session_repo, mock_user_repo, sample_session, sample_servant
):
    session_id = sample_session.id
    servant_id = sample_servant.id
    now = datetime.now(timezone.utc)

    mock_session_repo.get_session.return_value = sample_session
    mock_user_repo.get.return_value = sample_servant
    # Mock the check for existing records
    mock_session_repo.get_record_by_session_and_servant.return_value = None

    record = AttendanceRecord(
        id=uuid4(),
        session_id=session_id,
        servant_id=servant_id,
        status=AttendanceStatus.PRESENT,
        recorded_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    mock_session_repo.create_record.return_value = record
    mock_session_repo.enrich_record.return_value = {
        **record.model_dump(),
        "servant_name": "Jean Dupont",
        "recorded_by_name": "Admin",
        "created_at": now,
        "updated_at": now,
    }

    data = AttendanceRecordCreate(
        servant_id=servant_id, status=AttendanceStatus.PRESENT
    )

    result = await service.mark_attendance(session_id, data, uuid4())

    assert result.status == AttendanceStatus.PRESENT
    mock_session_repo.create_record.assert_called_once()
