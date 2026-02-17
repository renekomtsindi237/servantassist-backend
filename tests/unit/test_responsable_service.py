"""
Unit tests for ResponsableService (Council Meetings & RI Compliance).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.application.services.responsable_service import ResponsableService
from src.core.entities.council_meeting import CouncilAttendance, CouncilAttendanceStatus, CouncilMeeting
from src.core.entities.responsable import Nomination, NominationStatus, PosteResponsable
from src.presentation.schemas.responsable import (
    CouncilAttendanceRecord,
    CouncilAttendanceRecordList,
    CouncilMeetingCreate,
)


@pytest.fixture
def mock_nomination_repo():
    return AsyncMock()


@pytest.fixture
def mock_action_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_council_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_nomination_repo, mock_action_repo, mock_user_repo, mock_council_repo):
    return ResponsableService(mock_nomination_repo, mock_action_repo, mock_user_repo, mock_council_repo)


@pytest.mark.asyncio
async def test_create_council_meeting_success(service, mock_council_repo):
    data = CouncilMeetingCreate(
        meeting_date=datetime.now(timezone.utc),
        location="Salle Paroissiale",
        agenda="Election du nouveau secretaire",
    )
    mock_council_repo.create_meeting.return_value = CouncilMeeting(
        id=uuid4(), **data.model_dump(), created_by=uuid4(), created_at=datetime.now(timezone.utc)
    )

    result = await service.create_council_meeting(data, uuid4())
    assert result.location == "Salle Paroissiale"
    mock_council_repo.create_meeting.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_council_attendance_destitution(service, mock_council_repo, mock_nomination_repo):
    responsable_id = uuid4()
    # Mock 3 consecutive absences
    mock_council_repo.get_responsable_attendances.return_value = [
        CouncilAttendance(status=CouncilAttendanceStatus.ABSENT),
        CouncilAttendance(status=CouncilAttendanceStatus.ABSENT),
        CouncilAttendance(status=CouncilAttendanceStatus.ABSENT),
    ]

    nomination = Nomination(
        id=uuid4(),
        user_id=responsable_id,
        poste=PosteResponsable.CENSEUR,
        status=NominationStatus.ACTIVE,
        nominated_by=uuid4(),
    )
    mock_nomination_repo.get_active_by_user.return_value = [nomination]

    result = await service.monitor_council_attendance(responsable_id)

    assert result["destituted"] is True
    assert nomination.status == NominationStatus.REVOQUEE
    assert "Art 15" in nomination.notes
    mock_nomination_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_council_attendance_no_destitution(service, mock_council_repo):
    responsable_id = uuid4()
    # Mock mixed attendance
    mock_council_repo.get_responsable_attendances.return_value = [
        CouncilAttendance(status=CouncilAttendanceStatus.PRESENT),
        CouncilAttendance(status=CouncilAttendanceStatus.ABSENT),
        CouncilAttendance(status=CouncilAttendanceStatus.PRESENT),
    ]

    result = await service.monitor_council_attendance(responsable_id)
    assert result["destituted"] is False
