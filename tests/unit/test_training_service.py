"""
Unit tests for TrainingService (CHARGE_LITURGIE).
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.application.services.training_service import TrainingService
from src.core.entities.training import (
    TrainingSession, TrainingParticipation, TrainingMaterial,
    TrainingLevel, TrainingStatus, ParticipationStatus, MaterialType
)
from fastapi import HTTPException

@pytest.fixture
def mock_session_repo():
    return AsyncMock()

@pytest.fixture
def mock_participation_repo():
    return AsyncMock()

@pytest.fixture
def mock_material_repo():
    return AsyncMock()

@pytest.fixture
def mock_session_material_repo():
    return AsyncMock()

@pytest.fixture
def service(mock_session_repo, mock_participation_repo, mock_material_repo, mock_session_material_repo):
    return TrainingService(
        mock_session_repo, 
        mock_participation_repo, 
        mock_material_repo, 
        mock_session_material_repo
    )

@pytest.fixture
def sample_session():
    return TrainingSession(
        id=uuid4(),
        title="Formation Test",
        description="Description Test",
        level=TrainingLevel.DEBUTANT,
        date=datetime.now(timezone.utc),
        start_time="14:00",
        end_time="16:00",
        duration_minutes=120,
        location="Salle A",
        trainer_id=uuid4(),
        status=TrainingStatus.PLANIFIEE,
        created_by=uuid4()
    )

@pytest.mark.asyncio
async def test_create_session(service, mock_session_repo, sample_session):
    mock_session_repo.create.return_value = sample_session
    mock_session_repo.enrich_session.return_value = sample_session
    
    result = await service.create_session(
        title=sample_session.title,
        description=sample_session.description,
        level=sample_session.level,
        date=sample_session.date,
        start_time=sample_session.start_time,
        end_time=sample_session.end_time,
        duration_minutes=sample_session.duration_minutes,
        location=sample_session.location,
        trainer_id=sample_session.trainer_id,
        created_by=sample_session.created_by
    )
    
    assert result.title == sample_session.title
    mock_session_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_register_participant_success(service, mock_session_repo, mock_participation_repo, sample_session):
    mock_session_repo.get_by_id.return_value = sample_session
    mock_participation_repo.get_by_session_and_servant.return_value = None
    mock_participation_repo.list_by_session.return_value = []
    
    participation = TrainingParticipation(
        id=uuid4(),
        session_id=sample_session.id,
        servant_id=uuid4(),
        status=ParticipationStatus.INSCRIT,
        registered_by=uuid4()
    )
    mock_participation_repo.create.return_value = participation
    mock_participation_repo.enrich_participation.return_value = participation
    
    result = await service.register_participant(
        session_id=sample_session.id,
        servant_id=participation.servant_id,
        registered_by=participation.registered_by
    )
    
    assert result.servant_id == participation.servant_id
    mock_participation_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_register_participant_session_full(service, mock_session_repo, mock_participation_repo, sample_session):
    sample_session.max_participants = 1
    mock_session_repo.get_by_id.return_value = sample_session
    mock_participation_repo.get_by_session_and_servant.return_value = None
    mock_participation_repo.list_by_session.return_value = [MagicMock()]
    
    with pytest.raises(HTTPException) as exc:
        await service.register_participant(
            session_id=sample_session.id,
            servant_id=uuid4(),
            registered_by=uuid4()
        )
    assert exc.value.status_code == 400
    assert "Session is full" in exc.value.detail

@pytest.mark.asyncio
async def test_evaluate_participant(service, mock_participation_repo):
    participation_id = uuid4()
    participation = TrainingParticipation(
        id=participation_id,
        session_id=uuid4(),
        servant_id=uuid4(),
        status=ParticipationStatus.PRESENT,
        registered_by=uuid4()
    )
    mock_participation_repo.get_by_id.return_value = participation
    mock_participation_repo.update.return_value = participation
    mock_participation_repo.enrich_participation.return_value = participation
    
    result = await service.evaluate_participant(
        participation_id=participation_id,
        evaluation_score=90,
        evaluation_comments="Excellent",
        certificate_issued=True
    )
    
    assert result.evaluation_score == 90
    assert result.certificate_issued is True
    mock_participation_repo.update.assert_called_once()
