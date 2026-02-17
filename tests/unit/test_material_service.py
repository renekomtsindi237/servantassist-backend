"""
Unit tests for MaterialService (INTENDANTS).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.material_service import MaterialService
from src.core.entities.material import (
    AubeTask,
    CleaningTask,
    MaterialCategory,
    MaterialCondition,
    MaterialItem,
    TaskAssignment,
    TaskStatus,
    TaskType,
)


@pytest.fixture
def mock_item_repo():
    return AsyncMock()


@pytest.fixture
def mock_cleaning_task_repo():
    return AsyncMock()


@pytest.fixture
def mock_assignment_repo():
    return AsyncMock()


@pytest.fixture
def mock_aube_task_repo():
    return AsyncMock()


@pytest.fixture
def mock_maintenance_repo():
    return AsyncMock()


@pytest.fixture
def service(
    mock_item_repo,
    mock_cleaning_task_repo,
    mock_assignment_repo,
    mock_aube_task_repo,
    mock_maintenance_repo,
):
    return MaterialService(
        mock_item_repo,
        mock_cleaning_task_repo,
        mock_assignment_repo,
        mock_aube_task_repo,
        mock_maintenance_repo,
    )


@pytest.fixture
def sample_item():
    return MaterialItem(
        id=uuid4(),
        name="Aube Blanche",
        category=MaterialCategory.AUBE,
        quantity=10,
        location="Armoire 1",
        condition=MaterialCondition.BON,
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_create_item(service, mock_item_repo, sample_item):
    mock_item_repo.create.return_value = sample_item

    result = await service.create_item(
        name=sample_item.name,
        category=sample_item.category,
        quantity=sample_item.quantity,
        location=sample_item.location,
        created_by=sample_item.created_by,
    )

    assert result.name == sample_item.name
    mock_item_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_cleaning_task(service, mock_cleaning_task_repo):
    task_id = uuid4()
    task = CleaningTask(
        id=task_id,
        title="Nettoyage Sacristie",
        description="Nettoyage complet",
        task_type=TaskType.NETTOYAGE,
        scheduled_date=datetime.now(timezone.utc),
        scheduled_time="08:00",
        location="Sacristie",
        status=TaskStatus.PLANIFIEE,
        created_by=uuid4(),
    )
    mock_cleaning_task_repo.create.return_value = task

    result = await service.create_cleaning_task(
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        scheduled_date=task.scheduled_date,
        scheduled_time=task.scheduled_time,
        location=task.location,
        created_by=task.created_by,
    )

    assert result.title == task.title
    mock_cleaning_task_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_assign_servant_to_task(
    service, mock_cleaning_task_repo, mock_assignment_repo
):
    task_id = uuid4()
    servant_id = uuid4()
    assigned_by = uuid4()

    mock_cleaning_task_repo.get_by_id.return_value = MagicMock()
    assignment = TaskAssignment(
        id=uuid4(), task_id=task_id, servant_id=servant_id, assigned_by=assigned_by
    )
    mock_assignment_repo.create.return_value = assignment
    mock_assignment_repo.enrich_assignment.return_value = assignment

    result = await service.assign_servant_to_task(task_id, servant_id, assigned_by)

    assert result.task_id == task_id
    assert result.servant_id == servant_id
    mock_assignment_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_validate_cleaning_task_not_completed(service, mock_cleaning_task_repo):
    task_id = uuid4()
    task = CleaningTask(
        id=task_id,
        title="Test Task",
        description="Test",
        task_type=TaskType.NETTOYAGE,
        scheduled_date=datetime.now(timezone.utc),
        scheduled_time="08:00",
        location="Test",
        status=TaskStatus.PLANIFIEE,
        created_by=uuid4(),
    )
    mock_cleaning_task_repo.get_by_id.return_value = task

    with pytest.raises(HTTPException) as exc:
        await service.validate_cleaning_task(task_id, uuid4())

    assert exc.value.status_code == 400
    assert "Task must be completed" in exc.value.detail
