"""
Unit tests for SportCultureService (CHARGE_SPORT_CULTURE).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.application.services.sport_culture_service import SportCultureService
from src.core.entities.sport_culture import (
    EventStatus,
    EventType,
    ParticipationStatus,
    ResultType,
    SportCultureEvent,
    SportType,
)
from src.core.entities.user import User, UserRole


@pytest.fixture
def mock_event_repo():
    return AsyncMock()


@pytest.fixture
def mock_participation_repo():
    return AsyncMock()


@pytest.fixture
def mock_result_repo():
    return AsyncMock()


@pytest.fixture
def mock_team_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_event_repo, mock_participation_repo, mock_result_repo, mock_team_repo):
    return SportCultureService(mock_event_repo, mock_participation_repo, mock_result_repo, mock_team_repo)


@pytest.fixture
def sample_event():
    return SportCultureEvent(
        id=uuid4(),
        title="Foot Inter-groupes",
        description="Match amical contre St Jean",
        event_type=EventType.MATCH,
        sport_type=SportType.FOOTBALL,
        date=datetime(2026, 3, 15, tzinfo=timezone.utc),
        start_time="15h00",
        end_time="17h30",
        location="Terrain ISJ",
        max_participants=22,
        cost=500.0,
        status=EventStatus.PLANIFIE,
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_create_event(service, mock_event_repo, sample_event):
    mock_event_repo.create.return_value = sample_event

    result = await service.create_event(
        title=sample_event.title,
        description=sample_event.description,
        event_type=sample_event.event_type,
        date=sample_event.date,
        start_time=sample_event.start_time,
        end_time=sample_event.end_time,
        location=sample_event.location,
        max_participants=sample_event.max_participants,
        created_by=sample_event.created_by,
        sport_type=sample_event.sport_type,
        cost=sample_event.cost,
        broadcast_notification=False,
    )

    assert result.title == sample_event.title
    mock_event_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_participant_success(service, mock_event_repo, mock_participation_repo, sample_event):
    servant_id = uuid4()
    mock_event_repo.get_by_id.return_value = sample_event
    mock_participation_repo.get_by_event_and_servant.return_value = None
    mock_participation_repo.count_by_event.return_value = 5
    mock_participation_repo.create.return_value = MagicMock()
    mock_participation_repo.enrich_participation.return_value = MagicMock()

    await service.register_participant(sample_event.id, servant_id, uuid4())

    mock_participation_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_add_result(service, mock_event_repo, mock_result_repo, sample_event):
    mock_event_repo.get_by_id.return_value = sample_event
    mock_result_repo.create.return_value = MagicMock()

    await service.add_result(
        event_id=sample_event.id,
        result_type=ResultType.VICTOIRE,
        description="Gagné 2-0",
        recorded_by=uuid4(),
        team_name="Servants United",
        score=2,
        opponent_name="St Jean",
        opponent_score=0,
    )

    mock_result_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_team(service, mock_event_repo, mock_team_repo, sample_event):
    mock_event_repo.get_by_id.return_value = sample_event
    mock_team_repo.create.return_value = MagicMock()

    await service.create_team(
        event_id=sample_event.id,
        team_name="Equipe A",
        captain_id=uuid4(),
        members=[uuid4(), uuid4()],
        created_by=uuid4(),
    )

    mock_team_repo.create.assert_called_once()
