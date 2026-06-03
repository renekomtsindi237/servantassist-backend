"""
Unit tests for MaterialService (INTENDANTS).
Covers all CRUD methods, task management, assignments, and maintenance history.
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
    MaintenanceHistory,
    MaterialCategory,
    MaterialCondition,
    MaterialItem,
    TaskAssignment,
    TaskStatus,
    TaskType,
)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_item(**kwargs) -> MaterialItem:
    defaults = dict(
        id=uuid4(),
        name="Aube Blanche",
        category=MaterialCategory.AUBE,
        quantity=10,
        location="Armoire 1",
        condition=MaterialCondition.BON,
        created_by=uuid4(),
    )
    defaults.update(kwargs)
    return MaterialItem(**defaults)


def _make_task(**kwargs) -> CleaningTask:
    defaults = dict(
        id=uuid4(),
        title="Nettoyage Sacristie",
        description="Nettoyage complet",
        task_type=TaskType.NETTOYAGE,
        scheduled_date=datetime.now(timezone.utc),
        scheduled_time="08:00",
        location="Sacristie",
        status=TaskStatus.PLANIFIEE,
        created_by=uuid4(),
    )
    defaults.update(kwargs)
    return CleaningTask(**defaults)


def _make_aube_task(**kwargs) -> AubeTask:
    defaults = dict(
        id=uuid4(),
        title="Préparation Aubes",
        task_type=TaskType.LAVAGE,
        scheduled_date=datetime.now(timezone.utc),
        scheduled_time="05:30",
        location="Sacristie",
        aube_count=5,
        created_by=uuid4(),
    )
    defaults.update(kwargs)
    return AubeTask(**defaults)


def _make_assignment(task_id=None) -> TaskAssignment:
    return TaskAssignment(
        id=uuid4(),
        task_id=task_id or uuid4(),
        servant_id=uuid4(),
        assigned_by=uuid4(),
    )


def _make_svc(
    item_repo=None,
    cleaning_task_repo=None,
    assignment_repo=None,
    aube_task_repo=None,
    maintenance_repo=None,
) -> MaterialService:
    return MaterialService(
        item_repo=item_repo or AsyncMock(),
        cleaning_task_repo=cleaning_task_repo or AsyncMock(),
        assignment_repo=assignment_repo or AsyncMock(),
        aube_task_repo=aube_task_repo or AsyncMock(),
        maintenance_repo=maintenance_repo or AsyncMock(),
    )


# ══════════════════════════════════════════════════════════════════
#  Existing tests (kept)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_item():
    item_repo = AsyncMock()
    item = _make_item()
    item_repo.create.return_value = item

    svc = _make_svc(item_repo=item_repo)
    result = await svc.create_item(
        name=item.name,
        category=item.category,
        quantity=item.quantity,
        location=item.location,
        created_by=item.created_by,
    )

    assert result.name == item.name
    item_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_cleaning_task():
    cleaning_task_repo = AsyncMock()
    task = _make_task()
    cleaning_task_repo.create.return_value = task

    svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
    result = await svc.create_cleaning_task(
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        scheduled_date=task.scheduled_date,
        scheduled_time=task.scheduled_time,
        location=task.location,
        created_by=task.created_by,
    )

    assert result.title == task.title
    cleaning_task_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_assign_servant_to_task():
    cleaning_task_repo = AsyncMock()
    assignment_repo = AsyncMock()
    task = _make_task()
    cleaning_task_repo.get_by_id.return_value = task
    assignment = _make_assignment(task_id=task.id)
    assignment_repo.create.return_value = assignment
    assignment_repo.enrich_assignment.return_value = assignment

    svc = _make_svc(cleaning_task_repo=cleaning_task_repo, assignment_repo=assignment_repo)
    result = await svc.assign_servant_to_task(task.id, uuid4(), uuid4())

    assert result.task_id == task.id
    assignment_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_validate_cleaning_task_not_completed():
    cleaning_task_repo = AsyncMock()
    task = _make_task(status=TaskStatus.PLANIFIEE)
    cleaning_task_repo.get_by_id.return_value = task

    svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
    with pytest.raises(HTTPException) as exc:
        await svc.validate_cleaning_task(task.id, uuid4())
    assert exc.value.status_code == 400
    assert "Task must be completed" in exc.value.detail


# ══════════════════════════════════════════════════════════════════
#  Item CRUD
# ══════════════════════════════════════════════════════════════════


class TestGetItem:
    @pytest.mark.asyncio
    async def test_returns_item(self):
        item_repo = AsyncMock()
        item = _make_item()
        item_repo.get_by_id.return_value = item

        svc = _make_svc(item_repo=item_repo)
        result = await svc.get_item(item.id)
        assert result is item

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        item_repo = AsyncMock()
        item_repo.get_by_id.return_value = None

        svc = _make_svc(item_repo=item_repo)
        result = await svc.get_item(uuid4())
        assert result is None


class TestListItems:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        item_repo = AsyncMock()
        item = _make_item()
        item_repo.list_items.return_value = ([item], 1)

        svc = _make_svc(item_repo=item_repo)
        items, total = await svc.list_items(skip=0, limit=10)
        assert total == 1
        assert items[0] is item
        item_repo.list_items.assert_called_once()


class TestUpdateItem:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        item_repo = AsyncMock()
        item_repo.get_by_id.return_value = None

        svc = _make_svc(item_repo=item_repo)
        result = await svc.update_item(uuid4(), name="New Name")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_name_and_quantity(self):
        item_repo = AsyncMock()
        item = _make_item()
        item_repo.get_by_id.return_value = item
        item_repo.update.return_value = item

        svc = _make_svc(item_repo=item_repo)
        await svc.update_item(item.id, name="New Name", quantity=20)

        assert item.name == "New Name"
        assert item.quantity == 20
        item_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_none_fields(self):
        item_repo = AsyncMock()
        item = _make_item()
        original_name = item.name
        item_repo.get_by_id.return_value = item
        item_repo.update.return_value = item

        svc = _make_svc(item_repo=item_repo)
        await svc.update_item(item.id, location="New Location")

        assert item.name == original_name
        assert item.location == "New Location"


class TestDeleteItem:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        item_repo = AsyncMock()
        item_repo.delete.return_value = True

        svc = _make_svc(item_repo=item_repo)
        result = await svc.delete_item(uuid4())
        assert result is True


class TestGetItemsNeedingMaintenance:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        item_repo = AsyncMock()
        items = [_make_item(), _make_item()]
        item_repo.get_items_needing_maintenance.return_value = items

        svc = _make_svc(item_repo=item_repo)
        result = await svc.get_items_needing_maintenance()
        assert result is items


# ══════════════════════════════════════════════════════════════════
#  Cleaning task CRUD
# ══════════════════════════════════════════════════════════════════


class TestGetCleaningTask:
    @pytest.mark.asyncio
    async def test_returns_task(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task()
        cleaning_task_repo.get_by_id.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.get_cleaning_task(task.id)
        assert result is task

    @pytest.mark.asyncio
    async def test_returns_none(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.get_cleaning_task(uuid4())
        assert result is None


class TestListCleaningTasks:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task()
        cleaning_task_repo.list_tasks.return_value = ([task], 1)

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        tasks, total = await svc.list_cleaning_tasks()
        assert total == 1
        cleaning_task_repo.list_tasks.assert_called_once()


class TestUpdateCleaningTask:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.update_cleaning_task(uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task()
        cleaning_task_repo.get_by_id.return_value = task
        cleaning_task_repo.update.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        await svc.update_cleaning_task(
            task.id,
            title="Nouveau titre",
            status=TaskStatus.EN_COURS,
        )

        assert task.title == "Nouveau titre"
        assert task.status == TaskStatus.EN_COURS


class TestAddCleaningTaskPhoto:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.add_cleaning_task_photo(uuid4(), "http://photo.jpg", "before")
        assert result is None

    @pytest.mark.asyncio
    async def test_adds_before_photo(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task()
        task.photos_before = []
        cleaning_task_repo.get_by_id.return_value = task
        cleaning_task_repo.update.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        await svc.add_cleaning_task_photo(task.id, "http://before.jpg", "before")

        assert "http://before.jpg" in task.photos_before

    @pytest.mark.asyncio
    async def test_adds_after_photo(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task()
        task.photos_after = []
        cleaning_task_repo.get_by_id.return_value = task
        cleaning_task_repo.update.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        await svc.add_cleaning_task_photo(task.id, "http://after.jpg", "after")

        assert "http://after.jpg" in task.photos_after


class TestCompleteCleaningTask:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.complete_cleaning_task(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_sets_terminee_status(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task(status=TaskStatus.EN_COURS)
        cleaning_task_repo.get_by_id.return_value = task
        cleaning_task_repo.update.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        await svc.complete_cleaning_task(task.id, notes="Terminé avec succès")

        assert task.status == TaskStatus.TERMINEE
        assert task.notes == "Terminé avec succès"


class TestValidateCleaningTaskSuccess:
    @pytest.mark.asyncio
    async def test_validates_completed_task(self):
        cleaning_task_repo = AsyncMock()
        task = _make_task(status=TaskStatus.TERMINEE)
        cleaning_task_repo.get_by_id.return_value = task
        cleaning_task_repo.update.return_value = task

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        validated_by = uuid4()
        await svc.validate_cleaning_task(task.id, validated_by, notes="Validé")

        assert task.status == TaskStatus.VALIDEE
        assert task.validated_by == validated_by
        assert task.notes == "Validé"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.validate_cleaning_task(uuid4(), uuid4())
        assert result is None


class TestDeleteCleaningTask:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.delete.return_value = True

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        result = await svc.delete_cleaning_task(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Task assignments
# ══════════════════════════════════════════════════════════════════


class TestAssignServantToTaskErrors:
    @pytest.mark.asyncio
    async def test_raises_404_when_task_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.assign_servant_to_task(uuid4(), uuid4(), uuid4())
        assert exc.value.status_code == 404


class TestAssignServantsBatch:
    @pytest.mark.asyncio
    async def test_raises_404_when_task_not_found(self):
        cleaning_task_repo = AsyncMock()
        cleaning_task_repo.get_by_id.return_value = None

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.assign_servants_batch(uuid4(), [uuid4(), uuid4()], uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_creates_batch_assignments(self):
        cleaning_task_repo = AsyncMock()
        assignment_repo = AsyncMock()
        task = _make_task()
        cleaning_task_repo.get_by_id.return_value = task
        servant_ids = [uuid4(), uuid4()]
        assignments = [_make_assignment(task.id), _make_assignment(task.id)]
        assignment_repo.create_batch.return_value = assignments
        assignment_repo.enrich_assignment.side_effect = assignments

        svc = _make_svc(cleaning_task_repo=cleaning_task_repo, assignment_repo=assignment_repo)
        result = await svc.assign_servants_batch(task.id, servant_ids, uuid4())

        assignment_repo.create_batch.assert_called_once()
        assert len(result) == 2


class TestGetTaskAssignments:
    @pytest.mark.asyncio
    async def test_enriches_and_returns_list(self):
        assignment_repo = AsyncMock()
        assignments = [_make_assignment(), _make_assignment()]
        assignment_repo.get_by_task.return_value = assignments
        assignment_repo.enrich_assignment.side_effect = assignments

        svc = _make_svc(assignment_repo=assignment_repo)
        result = await svc.get_task_assignments(uuid4())

        assert len(result) == 2
        assert assignment_repo.enrich_assignment.call_count == 2


class TestGetServantAssignments:
    @pytest.mark.asyncio
    async def test_enriches_and_returns_list(self):
        assignment_repo = AsyncMock()
        assignment = _make_assignment()
        assignment_repo.get_by_servant.return_value = [assignment]
        assignment_repo.enrich_assignment.return_value = assignment

        svc = _make_svc(assignment_repo=assignment_repo)
        result = await svc.get_servant_assignments(uuid4())

        assert len(result) == 1


class TestRemoveAssignment:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        assignment_repo = AsyncMock()
        assignment_repo.delete.return_value = True

        svc = _make_svc(assignment_repo=assignment_repo)
        result = await svc.remove_assignment(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Aube task CRUD
# ══════════════════════════════════════════════════════════════════


class TestCreateAubeTask:
    @pytest.mark.asyncio
    async def test_creates_without_notification(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        aube_task_repo.create.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.create_aube_task(
            title=task.title,
            task_type=task.task_type,
            scheduled_date=task.scheduled_date,
            scheduled_time=task.scheduled_time,
            location=task.location,
            aube_count=task.aube_count,
            created_by=task.created_by,
            broadcast_notification=False,
        )

        aube_task_repo.create.assert_called_once()
        assert result.title == task.title


class TestGetAubeTask:
    @pytest.mark.asyncio
    async def test_returns_task(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        aube_task_repo.get_by_id.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.get_aube_task(task.id)
        assert result is task

    @pytest.mark.asyncio
    async def test_returns_none(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.get_by_id.return_value = None

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.get_aube_task(uuid4())
        assert result is None


class TestListAubeTasks:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        aube_task_repo.list_tasks.return_value = ([task], 1)

        svc = _make_svc(aube_task_repo=aube_task_repo)
        tasks, total = await svc.list_aube_tasks()
        assert total == 1


class TestUpdateAubeTask:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.get_by_id.return_value = None

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.update_aube_task(uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        aube_task_repo.get_by_id.return_value = task
        aube_task_repo.update.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        await svc.update_aube_task(task.id, title="Updated", aube_count=10)

        assert task.title == "Updated"
        assert task.aube_count == 10


class TestCompleteAubeTask:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.get_by_id.return_value = None

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.complete_aube_task(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_sets_terminee_status(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        task.status = TaskStatus.EN_COURS
        aube_task_repo.get_by_id.return_value = task
        aube_task_repo.update.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        await svc.complete_aube_task(task.id, photos_after=["photo.jpg"])

        assert task.status == TaskStatus.TERMINEE
        assert task.photos_after == ["photo.jpg"]


class TestAddAubeTaskPhoto:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.get_by_id.return_value = None

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.add_aube_task_photo(uuid4(), "photo.jpg", "before")
        assert result is None

    @pytest.mark.asyncio
    async def test_adds_before_photo(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        task.photos_before = []
        aube_task_repo.get_by_id.return_value = task
        aube_task_repo.update.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        await svc.add_aube_task_photo(task.id, "before.jpg", "before")
        assert "before.jpg" in task.photos_before

    @pytest.mark.asyncio
    async def test_adds_after_photo(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        task.photos_after = []
        aube_task_repo.get_by_id.return_value = task
        aube_task_repo.update.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        await svc.add_aube_task_photo(task.id, "after.jpg", "after")
        assert "after.jpg" in task.photos_after


class TestValidateAubeTask:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.get_by_id.return_value = None

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.validate_aube_task(uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_raises_400_when_not_terminee(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        task.status = TaskStatus.PLANIFIEE
        aube_task_repo.get_by_id.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.validate_aube_task(task.id, uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_validates_terminee_task(self):
        aube_task_repo = AsyncMock()
        task = _make_aube_task()
        task.status = TaskStatus.TERMINEE
        aube_task_repo.get_by_id.return_value = task
        aube_task_repo.update.return_value = task

        svc = _make_svc(aube_task_repo=aube_task_repo)
        validated_by = uuid4()
        await svc.validate_aube_task(task.id, validated_by)

        assert task.status == TaskStatus.VALIDEE
        assert task.validated_by == validated_by


class TestDeleteAubeTask:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        aube_task_repo = AsyncMock()
        aube_task_repo.delete.return_value = True

        svc = _make_svc(aube_task_repo=aube_task_repo)
        result = await svc.delete_aube_task(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Maintenance history
# ══════════════════════════════════════════════════════════════════


class TestAddMaintenanceHistory:
    @pytest.mark.asyncio
    async def test_returns_none_when_item_not_found(self):
        item_repo = AsyncMock()
        item_repo.get_by_id.return_value = None

        svc = _make_svc(item_repo=item_repo)
        result = await svc.add_maintenance_history(
            item_id=uuid4(),
            maintenance_type=TaskType.NETTOYAGE,
            description="Nettoyage complet",
            performed_date=datetime.now(timezone.utc),
            performed_by=uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_history_and_updates_item(self):
        item_repo = AsyncMock()
        maintenance_repo = AsyncMock()
        item = _make_item()
        item_repo.get_by_id.return_value = item
        history = MagicMock(spec=MaintenanceHistory)
        maintenance_repo.create.return_value = history

        svc = _make_svc(item_repo=item_repo, maintenance_repo=maintenance_repo)
        performed_date = datetime.now(timezone.utc)
        result = await svc.add_maintenance_history(
            item_id=item.id,
            maintenance_type=TaskType.NETTOYAGE,
            description="Nettoyage",
            performed_date=performed_date,
            performed_by=uuid4(),
        )

        assert item.last_maintenance_date == performed_date
        item_repo.update.assert_called_once_with(item)
        maintenance_repo.create.assert_called_once()
        assert result is history


class TestGetItemMaintenanceHistory:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        maintenance_repo = AsyncMock()
        history_list = [MagicMock(), MagicMock()]
        maintenance_repo.get_by_item.return_value = history_list

        svc = _make_svc(maintenance_repo=maintenance_repo)
        result = await svc.get_item_maintenance_history(uuid4())
        assert result is history_list


# ══════════════════════════════════════════════════════════════════
#  Statistics and reports
# ══════════════════════════════════════════════════════════════════


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_returns_stats_dict(self):
        item_repo = AsyncMock()
        cleaning_task_repo = AsyncMock()
        aube_task_repo = AsyncMock()

        item = _make_item()
        item.category = MaterialCategory.AUBE
        item.condition = MaterialCondition.BON
        item_repo.list_items.return_value = ([item], 1)
        item_repo.get_items_needing_maintenance.return_value = []
        cleaning_task_repo.list_tasks.return_value = ([], 0)
        aube_task_repo.list_tasks.return_value = ([], 0)

        svc = _make_svc(
            item_repo=item_repo,
            cleaning_task_repo=cleaning_task_repo,
            aube_task_repo=aube_task_repo,
        )
        result = await svc.get_statistics()

        assert "total_items" in result
        assert result["total_items"] == 1
        assert "completion_rate" in result


class TestGetAttentionReason:
    def test_a_nettoyer(self):
        svc = _make_svc()
        item = _make_item(condition=MaterialCondition.A_NETTOYER)
        assert svc._get_attention_reason(item) == "À nettoyer"

    def test_a_reparer(self):
        svc = _make_svc()
        item = _make_item(condition=MaterialCondition.A_REPARER)
        assert svc._get_attention_reason(item) == "À réparer"

    def test_hors_service(self):
        svc = _make_svc()
        item = _make_item(condition=MaterialCondition.HORS_SERVICE)
        assert svc._get_attention_reason(item) == "Hors service"

    def test_default_reason(self):
        svc = _make_svc()
        item = _make_item(condition=MaterialCondition.BON)
        item.next_maintenance_date = None
        assert svc._get_attention_reason(item) == "Nécessite attention"
