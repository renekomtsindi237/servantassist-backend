"""
Unit tests for MaterialItemRepository, CleaningTaskRepository, TaskAssignmentRepository,
and AubeTaskRepository.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _sa_exec_result(scalar_one=None, scalars_list=None, scalar=None):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one)
    r.scalar = MagicMock(return_value=scalar)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    return r


# ═══════════════════════════════════════════════════════════════════════════════
#  MaterialItemRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_item(**kw):
    from src.core.entities.material import MaterialCategory, MaterialCondition

    m = MagicMock()
    m.id = kw.get("id", uuid4())
    m.name = kw.get("name", "Aube test")
    m.category = kw.get("category", MaterialCategory.AUBE)
    m.condition = kw.get("condition", MaterialCondition.BON)
    m.next_maintenance_date = kw.get("next_maintenance_date", None)
    m.description = kw.get("description", "Aube test description")
    m.updated_at = kw.get("updated_at", datetime.utcnow())
    return m


@pytest.mark.asyncio
async def test_material_item_create():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    item = _make_item()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(item)
    assert result is item


@pytest.mark.asyncio
async def test_material_item_get_by_id_found():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    item = _make_item()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=item))

    result = await repo.get_by_id(item.id)
    assert result is item


@pytest.mark.asyncio
async def test_material_item_get_by_id_not_found():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_material_item_list_items():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    items = [_make_item(), _make_item()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=2),  # count
            _sa_exec_result(scalars_list=items),  # items
        ]
    )

    result, total = await repo.list_items()
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_material_item_list_items_with_filters():
    from src.core.entities.material import MaterialCategory, MaterialCondition
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=0),
            _sa_exec_result(scalars_list=[]),
        ]
    )

    result, total = await repo.list_items(
        category=MaterialCategory.AUBE,
        condition=MaterialCondition.BON,
        search="test",
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_material_item_update():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    item = _make_item()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(item)
    assert result is item


@pytest.mark.asyncio
async def test_material_item_delete_found():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    item = _make_item()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=item))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(item.id)
    assert result is True


@pytest.mark.asyncio
async def test_material_item_delete_not_found():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_material_item_get_needs_maintenance():
    from src.infrastructure.repositories.material_repository import MaterialItemRepository

    session = _mock_session()
    repo = MaterialItemRepository(session)
    items = [_make_item()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=items))

    result = await repo.get_items_needing_maintenance()
    assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
#  CleaningTaskRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_task(**kw):
    from src.core.entities.material import CleaningTask, TaskStatus, TaskType

    t = MagicMock()
    t.id = kw.get("id", uuid4())
    t.task_type = kw.get("task_type", TaskType.NETTOYAGE)
    t.status = kw.get("status", TaskStatus.PLANIFIEE)
    t.scheduled_date = kw.get("scheduled_date", datetime.utcnow())
    t.updated_at = kw.get("updated_at", datetime.utcnow())
    return t


@pytest.mark.asyncio
async def test_cleaning_task_create():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    task = _make_task()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(task)
    assert result is task


@pytest.mark.asyncio
async def test_cleaning_task_get_by_id_found():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    task = _make_task()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=task))

    result = await repo.get_by_id(task.id)
    assert result is task


@pytest.mark.asyncio
async def test_cleaning_task_list_tasks():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    tasks = [_make_task()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=1),
            _sa_exec_result(scalars_list=tasks),
        ]
    )

    result, total = await repo.list_tasks()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_cleaning_task_list_tasks_with_filters():
    from src.core.entities.material import TaskStatus, TaskType
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    now = datetime.utcnow()
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=0),
            _sa_exec_result(scalars_list=[]),
        ]
    )

    result, total = await repo.list_tasks(
        task_type=TaskType.NETTOYAGE,
        status=TaskStatus.PLANIFIEE,
        start_date=now,
        end_date=now + timedelta(days=7),
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_cleaning_task_update():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    task = _make_task()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(task)
    assert result is task


@pytest.mark.asyncio
async def test_cleaning_task_delete_found():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    task = _make_task()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=task))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(task.id)
    assert result is True


@pytest.mark.asyncio
async def test_cleaning_task_delete_not_found():
    from src.infrastructure.repositories.material_repository import CleaningTaskRepository

    session = _mock_session()
    repo = CleaningTaskRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
#  TaskAssignmentRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_assignment(**kw):
    from src.core.entities.material import TaskAssignment

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.task_id = kw.get("task_id", uuid4())
    a.servant_id = kw.get("servant_id", uuid4())
    a.servant_name = kw.get("servant_name", None)
    return a


@pytest.mark.asyncio
async def test_task_assignment_create():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    a = _make_assignment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(a)
    assert result is a


@pytest.mark.asyncio
async def test_task_assignment_create_batch():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    assignments = [_make_assignment(), _make_assignment()]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_batch(assignments)
    assert len(result) == 2
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_task_assignment_get_by_task():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    assignments = [_make_assignment(), _make_assignment()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=assignments))

    result = await repo.get_by_task(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_task_assignment_get_by_servant():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    assignments = [_make_assignment()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=assignments))
    now = datetime.utcnow()

    result = await repo.get_by_servant(uuid4(), start_date=now, end_date=now + timedelta(days=7))
    assert len(result) == 1


@pytest.mark.asyncio
async def test_task_assignment_delete_found():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    a = _make_assignment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=a))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(a.id)
    assert result is True


@pytest.mark.asyncio
async def test_task_assignment_delete_not_found():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_task_assignment_enrich():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    a = _make_assignment()

    servant = MagicMock()
    servant.first_name = "Jean"
    servant.last_name = "Nkemelu"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=servant))

    with patch("src.infrastructure.repositories.material_repository.decrypt_str_fields"):
        await repo.enrich_assignment(a)

    assert a.servant_name == "Jean Nkemelu"


@pytest.mark.asyncio
async def test_task_assignment_enrich_no_servant():
    from src.infrastructure.repositories.material_repository import TaskAssignmentRepository

    session = _mock_session()
    repo = TaskAssignmentRepository(session)
    a = _make_assignment()

    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_assignment(a)
    # servant_name stays unchanged (None by default)
    assert result is a
