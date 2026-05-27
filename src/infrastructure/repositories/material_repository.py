"""
Repository pour la gestion du matériel (INTENDANTS).
"""
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.core.entities.user import User, UserRole
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name")


class MaterialItemRepository:
    """Repository pour les articles de matériel."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, item: MaterialItem) -> MaterialItem:
        """Crée un nouvel article."""
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_by_id(self, item_id: UUID) -> Optional[MaterialItem]:
        """Récupère un article par son ID."""
        result = await self.session.execute(
            select(MaterialItem).where(MaterialItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_items(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[MaterialCategory] = None,
        condition: Optional[MaterialCondition] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[MaterialItem], int]:
        """Liste les articles avec filtres."""
        query = select(MaterialItem)

        # Filtres
        if category:
            query = query.where(MaterialItem.category == category)
        if condition:
            query = query.where(MaterialItem.condition == condition)
        if search:
            query = query.where(
                MaterialItem.name.ilike(f"%{search}%")
                | MaterialItem.description.ilike(f"%{search}%")
            )

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(MaterialItem.name)
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update(self, item: MaterialItem) -> MaterialItem:
        """Met à jour un article."""
        item.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item_id: UUID) -> bool:
        """Supprime un article."""
        item = await self.get_by_id(item_id)
        if not item:
            return False

        await self.session.delete(item)
        await self.session.commit()
        return True

    async def get_items_needing_maintenance(self) -> List[MaterialItem]:
        """Récupère les articles nécessitant une maintenance."""
        now = utc_now()
        result = await self.session.execute(
            select(MaterialItem).where(
                (MaterialItem.next_maintenance_date <= now)
                | (
                    MaterialItem.condition.in_(
                        [MaterialCondition.A_NETTOYER, MaterialCondition.A_REPARER]
                    )
                )
            )
        )
        return list(result.scalars().all())


class CleaningTaskRepository:
    """Repository pour les tâches de nettoyage."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: CleaningTask) -> CleaningTask:
        """Crée une nouvelle tâche."""
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Optional[CleaningTask]:
        """Récupère une tâche par son ID."""
        result = await self.session.execute(
            select(CleaningTask).where(CleaningTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 50,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[CleaningTask], int]:
        """Liste les tâches avec filtres."""
        query = select(CleaningTask)

        # Filtres
        if task_type:
            query = query.where(CleaningTask.task_type == task_type)
        if status:
            query = query.where(CleaningTask.status == status)
        if start_date:
            query = query.where(CleaningTask.scheduled_date >= start_date)
        if end_date:
            query = query.where(CleaningTask.scheduled_date <= end_date)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(CleaningTask.scheduled_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def update(self, task: CleaningTask) -> CleaningTask:
        """Met à jour une tâche."""
        task.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task_id: UUID) -> bool:
        """Supprime une tâche."""
        task = await self.get_by_id(task_id)
        if not task:
            return False

        await self.session.delete(task)
        await self.session.commit()
        return True


class TaskAssignmentRepository:
    """Repository pour les assignations de tâches."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, assignment: TaskAssignment) -> TaskAssignment:
        """Crée une nouvelle assignation."""
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def create_batch(
        self, assignments: List[TaskAssignment]
    ) -> List[TaskAssignment]:
        """Crée plusieurs assignations en batch."""
        for assignment in assignments:
            self.session.add(assignment)
        await self.session.commit()
        for assignment in assignments:
            await self.session.refresh(assignment)
        return assignments

    async def get_by_task(self, task_id: UUID) -> List[TaskAssignment]:
        """Récupère les assignations d'une tâche."""
        result = await self.session.execute(
            select(TaskAssignment).where(TaskAssignment.task_id == task_id)
        )
        return list(result.scalars().all())

    async def get_by_servant(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TaskAssignment]:
        """Récupère les assignations d'un servant."""
        # Joindre avec les tâches pour filtrer par date
        query = (
            select(TaskAssignment)
            .join(CleaningTask, TaskAssignment.task_id == CleaningTask.id)
            .where(TaskAssignment.servant_id == servant_id)
        )

        if start_date:
            query = query.where(CleaningTask.scheduled_date >= start_date)
        if end_date:
            query = query.where(CleaningTask.scheduled_date <= end_date)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, assignment_id: UUID) -> bool:
        """Supprime une assignation."""
        result = await self.session.execute(
            select(TaskAssignment).where(TaskAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return False

        await self.session.delete(assignment)
        await self.session.commit()
        return True

    async def enrich_assignment(self, assignment: TaskAssignment) -> TaskAssignment:
        """Enrichit une assignation avec les noms."""
        # Récupérer le nom du servant
        servant_result = await self.session.execute(
            select(User).where(User.id == assignment.servant_id)
        )
        servant = servant_result.scalar_one_or_none()
        if servant:
            decrypt_str_fields(servant, _USER_PII)
            assignment.servant_name = f"{servant.first_name} {servant.last_name}"

        return assignment


class AubeTaskRepository:
    """Repository pour les tâches d'aubes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: AubeTask) -> AubeTask:
        """Crée une nouvelle tâche d'aubes."""
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Optional[AubeTask]:
        """Récupère une tâche par son ID."""
        result = await self.session.execute(
            select(AubeTask).where(AubeTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 50,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[AubeTask], int]:
        """Liste les tâches d'aubes avec filtres."""
        query = select(AubeTask)

        # Filtres
        if task_type:
            query = query.where(AubeTask.task_type == task_type)
        if status:
            query = query.where(AubeTask.status == status)
        if start_date:
            query = query.where(AubeTask.scheduled_date >= start_date)
        if end_date:
            query = query.where(AubeTask.scheduled_date <= end_date)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(AubeTask.scheduled_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def update(self, task: AubeTask) -> AubeTask:
        """Met à jour une tâche."""
        task.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task_id: UUID) -> bool:
        """Supprime une tâche."""
        task = await self.get_by_id(task_id)
        if not task:
            return False

        await self.session.delete(task)
        await self.session.commit()
        return True


class MaintenanceHistoryRepository:
    """Repository pour l'historique de maintenance."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, history: MaintenanceHistory) -> MaintenanceHistory:
        """Crée un nouvel historique."""
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_by_item(self, item_id: UUID) -> List[MaintenanceHistory]:
        """Récupère l'historique d'un article."""
        result = await self.session.execute(
            select(MaintenanceHistory)
            .where(MaintenanceHistory.item_id == item_id)
            .order_by(MaintenanceHistory.performed_date.desc())
        )
        return list(result.scalars().all())

    async def get_total_cost(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calcule le coût total de maintenance pour une période."""
        result = await self.session.execute(
            select(func.sum(MaintenanceHistory.cost)).where(
                and_(
                    MaintenanceHistory.performed_date >= start_date,
                    MaintenanceHistory.performed_date <= end_date,
                    MaintenanceHistory.cost.isnot(None),
                )
            )
        )
        total = result.scalar()
        return total or 0.0
