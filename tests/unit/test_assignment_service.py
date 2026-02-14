"""
Unit tests for AssignmentService.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit

from src.application.services.assignment_service import AssignmentService
from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.user import User, UserRole
from src.presentation.schemas.assignment import AssignmentCreate, AssignmentStatusUpdate
from fastapi import HTTPException

@pytest.fixture
def mock_assignment_repo():
    return AsyncMock()

@pytest.fixture
def mock_event_repo():
    return AsyncMock()

@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def service(mock_assignment_repo, mock_event_repo, mock_user_repo):
    return AssignmentService(mock_assignment_repo, mock_event_repo, mock_user_repo)

@pytest.fixture
def sample_assignment():
    return Assignment(
        id=uuid4(),
        event_id=uuid4(),
        user_id=uuid4(),
        liturgical_role=LiturgicalRole.ACOLYTE,
        status=AssignmentStatus.PENDING,
        assigned_by=uuid4()
    )

@pytest.mark.asyncio
async def test_create_assignment_success(service, mock_assignment_repo, mock_event_repo, mock_user_repo, sample_assignment):
    mock_event_repo.get.return_value = MagicMock()
    mock_user_repo.get.return_value = User(id=sample_assignment.user_id, role=UserRole.SERVANT, is_active=True)
    mock_assignment_repo.get_by_event_user_role.return_value = []
    mock_assignment_repo.create.return_value = sample_assignment
    
    # Return a dict for enrichment as expected by the service which then wraps it in a Response schema
    mock_assignment_repo.enrich_assignment.return_value = {
        **sample_assignment.model_dump(),
        "user_name": "Jean Dupont",
        "event_title": "Messe",
        "assigned_by_name": "Admin",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    data = AssignmentCreate(
        event_id=sample_assignment.event_id,
        user_id=sample_assignment.user_id,
        liturgical_role=sample_assignment.liturgical_role
    )
    
    result = await service.create_assignment(
        data=data,
        assigned_by=sample_assignment.assigned_by
    )
    
    assert result.liturgical_role == LiturgicalRole.ACOLYTE
    mock_assignment_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_update_my_status_success(service, mock_assignment_repo, sample_assignment):
    mock_assignment_repo.get.return_value = sample_assignment
    mock_assignment_repo.update.return_value = sample_assignment
    mock_assignment_repo.enrich_assignment.return_value = {
        **sample_assignment.model_dump(),
        "user_name": "Jean Dupont",
        "event_title": "Messe",
        "assigned_by_name": "Admin",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    data = AssignmentStatusUpdate(status=AssignmentStatus.ACCEPTED)
    
    # Signature: update_my_status(assignment_id, data, user_id)
    await service.update_my_status(sample_assignment.id, data, sample_assignment.user_id)
    
    mock_assignment_repo.update.assert_called_once()

@pytest.mark.asyncio
async def test_mark_presence_success(service, mock_assignment_repo, sample_assignment):
    mock_assignment_repo.get.return_value = sample_assignment
    mock_assignment_repo.update.return_value = sample_assignment
    mock_assignment_repo.enrich_assignment.return_value = {
        **sample_assignment.model_dump(),
        "user_name": "Jean Dupont",
        "event_title": "Messe",
        "assigned_by_name": "Admin",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await service.mark_presence(sample_assignment.id, True, uuid4())
    
    mock_assignment_repo.update.assert_called_once()
