"""
Service pour la gestion du matériel (INTENDANTS).
"""
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from src.core.entities.material import (
    AubeTask,
    CleaningTask,
    MaintenanceHistory,
    MaterialCategory,
    MaterialCondition,
    MaterialItem,
    MaterialReport,
    TaskAssignment,
    TaskStatus,
    TaskType,
)
from src.core.interfaces.repositories import (
    IAubeTaskRepository,
    ICleaningTaskRepository,
    IMaintenanceHistoryRepository,
    IMaterialItemRepository,
    ITaskAssignmentRepository,
)


class MaterialService:
    """Service de gestion du matériel."""

    def __init__(
        self,
        item_repo: IMaterialItemRepository,
        cleaning_task_repo: ICleaningTaskRepository,
        assignment_repo: ITaskAssignmentRepository,
        aube_task_repo: IAubeTaskRepository,
        maintenance_repo: IMaintenanceHistoryRepository,
    ):
        self.item_repo = item_repo
        self.cleaning_task_repo = cleaning_task_repo
        self.assignment_repo = assignment_repo
        self.aube_task_repo = aube_task_repo
        self.maintenance_repo = maintenance_repo

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ARTICLES
    # ══════════════════════════════════════════════════════════════════

    async def create_item(
        self,
        name: str,
        category: MaterialCategory,
        quantity: int,
        location: str,
        created_by: UUID,
        description: Optional[str] = None,
        size: Optional[str] = None,
        condition: MaterialCondition = MaterialCondition.BON,
        purchase_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> MaterialItem:
        """Crée un nouvel article de matériel."""
        item = MaterialItem(
            id=uuid4(),
            name=name,
            category=category,
            description=description,
            quantity=quantity,
            size=size,
            condition=condition,
            location=location,
            purchase_date=purchase_date,
            notes=notes,
            photo_url=photo_url,
            created_by=created_by,
        )

        return await self.item_repo.create(item)

    async def get_item(self, item_id: UUID) -> Optional[MaterialItem]:
        """Récupère un article par son ID."""
        return await self.item_repo.get_by_id(item_id)

    async def list_items(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[MaterialCategory] = None,
        condition: Optional[MaterialCondition] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[MaterialItem], int]:
        """Liste les articles avec filtres."""
        return await self.item_repo.list_items(
            skip=skip,
            limit=limit,
            category=category,
            condition=condition,
            search=search,
        )

    async def update_item(
        self,
        item_id: UUID,
        name: Optional[str] = None,
        category: Optional[MaterialCategory] = None,
        description: Optional[str] = None,
        quantity: Optional[int] = None,
        size: Optional[str] = None,
        condition: Optional[MaterialCondition] = None,
        location: Optional[str] = None,
        purchase_date: Optional[datetime] = None,
        last_maintenance_date: Optional[datetime] = None,
        next_maintenance_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> Optional[MaterialItem]:
        """Met à jour un article."""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            return None

        # Mise à jour des champs
        if name is not None:
            item.name = name
        if category is not None:
            item.category = category
        if description is not None:
            item.description = description
        if quantity is not None:
            item.quantity = quantity
        if size is not None:
            item.size = size
        if condition is not None:
            item.condition = condition
        if location is not None:
            item.location = location
        if purchase_date is not None:
            item.purchase_date = purchase_date
        if last_maintenance_date is not None:
            item.last_maintenance_date = last_maintenance_date
        if next_maintenance_date is not None:
            item.next_maintenance_date = next_maintenance_date
        if notes is not None:
            item.notes = notes
        if photo_url is not None:
            item.photo_url = photo_url

        return await self.item_repo.update(item)

    async def delete_item(self, item_id: UUID) -> bool:
        """Supprime un article."""
        return await self.item_repo.delete(item_id)

    async def get_items_needing_maintenance(self) -> List[MaterialItem]:
        """Récupère les articles nécessitant une maintenance."""
        return await self.item_repo.get_items_needing_maintenance()

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES TÂCHES DE NETTOYAGE
    # ══════════════════════════════════════════════════════════════════

    async def create_cleaning_task(
        self,
        title: str,
        description: str,
        task_type: TaskType,
        scheduled_date: datetime,
        scheduled_time: str,
        location: str,
        created_by: UUID,
        items: List[str] = None,
        notes: Optional[str] = None,
    ) -> CleaningTask:
        """Crée une nouvelle tâche de nettoyage."""
        task = CleaningTask(
            id=uuid4(),
            title=title,
            description=description,
            task_type=task_type,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            location=location,
            items=items or [],
            notes=notes,
            created_by=created_by,
        )

        return await self.cleaning_task_repo.create(task)

    async def get_cleaning_task(self, task_id: UUID) -> Optional[CleaningTask]:
        """Récupère une tâche par son ID."""
        return await self.cleaning_task_repo.get_by_id(task_id)

    async def list_cleaning_tasks(
        self,
        skip: int = 0,
        limit: int = 50,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[CleaningTask], int]:
        """Liste les tâches avec filtres."""
        return await self.cleaning_task_repo.list_tasks(
            skip=skip,
            limit=limit,
            task_type=task_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    async def update_cleaning_task(
        self,
        task_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        scheduled_date: Optional[datetime] = None,
        scheduled_time: Optional[str] = None,
        location: Optional[str] = None,
        items: Optional[List[str]] = None,
        status: Optional[TaskStatus] = None,
        notes: Optional[str] = None,
    ) -> Optional[CleaningTask]:
        """Met à jour une tâche."""
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            return None

        # Mise à jour des champs
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if task_type is not None:
            task.task_type = task_type
        if scheduled_date is not None:
            task.scheduled_date = scheduled_date
        if scheduled_time is not None:
            task.scheduled_time = scheduled_time
        if location is not None:
            task.location = location
        if items is not None:
            task.items = items
        if status is not None:
            task.status = status
        if notes is not None:
            task.notes = notes

        return await self.cleaning_task_repo.update(task)

    async def add_cleaning_task_photo(
        self,
        task_id: UUID,
        photo_url: str,
        phase: str,  # "before" | "after"
    ) -> Optional[CleaningTask]:
        """Ajoute une photo avant ou après à une tâche de nettoyage."""
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            return None
        if phase == "before":
            task.photos_before = list(task.photos_before or []) + [photo_url]
        else:
            task.photos_after = list(task.photos_after or []) + [photo_url]
        return await self.cleaning_task_repo.update(task)

    async def complete_cleaning_task(
        self,
        task_id: UUID,
        photos_after: List[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[CleaningTask]:
        """Marque une tâche comme terminée."""
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.TERMINEE
        task.completed_at = utc_now()
        if photos_after:
            task.photos_after = photos_after
        if notes:
            task.notes = notes

        return await self.cleaning_task_repo.update(task)

    async def validate_cleaning_task(
        self,
        task_id: UUID,
        validated_by: UUID,
        notes: Optional[str] = None,
    ) -> Optional[CleaningTask]:
        """Valide une tâche terminée."""
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            return None

        if task.status != TaskStatus.TERMINEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task must be completed before validation",
            )

        task.status = TaskStatus.VALIDEE
        task.validated_at = utc_now()
        task.validated_by = validated_by
        if notes:
            task.notes = notes

        return await self.cleaning_task_repo.update(task)

    async def delete_cleaning_task(self, task_id: UUID) -> bool:
        """Supprime une tâche."""
        return await self.cleaning_task_repo.delete(task_id)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ASSIGNATIONS
    # ══════════════════════════════════════════════════════════════════

    async def assign_servant_to_task(
        self,
        task_id: UUID,
        servant_id: UUID,
        assigned_by: UUID,
    ) -> TaskAssignment:
        """Assigne un servant à une tâche."""
        # Vérifier que la tâche existe
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cette tâche est introuvable.",
            )

        assignment = TaskAssignment(
            id=uuid4(),
            task_id=task_id,
            servant_id=servant_id,
            assigned_by=assigned_by,
        )

        created = await self.assignment_repo.create(assignment)
        return await self.assignment_repo.enrich_assignment(created)

    async def assign_servants_batch(
        self,
        task_id: UUID,
        servant_ids: List[UUID],
        assigned_by: UUID,
    ) -> List[TaskAssignment]:
        """Assigne plusieurs servants à une tâche."""
        # Vérifier que la tâche existe
        task = await self.cleaning_task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cette tâche est introuvable.",
            )

        assignments = []
        for servant_id in servant_ids:
            assignment = TaskAssignment(
                id=uuid4(),
                task_id=task_id,
                servant_id=servant_id,
                assigned_by=assigned_by,
            )
            assignments.append(assignment)

        created_assignments = await self.assignment_repo.create_batch(assignments)

        # Enrichir les assignations
        enriched = []
        for assignment in created_assignments:
            enriched_assignment = await self.assignment_repo.enrich_assignment(
                assignment
            )
            enriched.append(enriched_assignment)

        return enriched

    async def get_task_assignments(self, task_id: UUID) -> List[TaskAssignment]:
        """Récupère les assignations d'une tâche."""
        assignments = await self.assignment_repo.get_by_task(task_id)

        # Enrichir les assignations
        enriched = []
        for assignment in assignments:
            enriched_assignment = await self.assignment_repo.enrich_assignment(
                assignment
            )
            enriched.append(enriched_assignment)

        return enriched

    async def get_servant_assignments(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TaskAssignment]:
        """Récupère les assignations d'un servant."""
        assignments = await self.assignment_repo.get_by_servant(
            servant_id, start_date, end_date
        )

        # Enrichir les assignations
        enriched = []
        for assignment in assignments:
            enriched_assignment = await self.assignment_repo.enrich_assignment(
                assignment
            )
            enriched.append(enriched_assignment)

        return enriched

    async def remove_assignment(self, assignment_id: UUID) -> bool:
        """Retire une assignation."""
        return await self.assignment_repo.delete(assignment_id)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES TÂCHES D'AUBES
    # ══════════════════════════════════════════════════════════════════

    async def create_aube_task(
        self,
        title: str,
        task_type: TaskType,
        scheduled_date: datetime,
        scheduled_time: str,
        location: str,
        aube_count: int,
        created_by: UUID,
        aube_sizes: List[str] = None,
        notes: Optional[str] = None,
        broadcast_notification: bool = True,
    ) -> AubeTask:
        """Crée une nouvelle tâche d'aubes."""
        task = AubeTask(
            id=uuid4(),
            title=title,
            task_type=task_type,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            location=location,
            aube_count=aube_count,
            aube_sizes=aube_sizes or [],
            notes=notes,
            broadcast_notification=broadcast_notification,
            created_by=created_by,
        )

        task = await self.aube_task_repo.create(task)

        if broadcast_notification:
            from src.application.services.notification_service import (
                NotificationService,
            )
            from src.core.entities.notification import (
                NotificationChannel,
                NotificationPriority,
                NotificationType,
            )

            notif_service = NotificationService(self.aube_task_repo.session)
            await notif_service.broadcast(
                target="servants",
                notification_type=NotificationType.GENERAL,
                channel=NotificationChannel.IN_APP,
                priority=NotificationPriority.NORMAL,
                title=f"Tâche d'aubes : {task.title}",
                body=(
                    f"Une tâche d'aubes a été planifiée le "
                    f"{task.scheduled_date.strftime('%d/%m/%Y')} "
                    f"à {task.scheduled_time} — {task.location}."
                ),
                sent_by=task.created_by,
            )

        return task

    async def get_aube_task(self, task_id: UUID) -> Optional[AubeTask]:
        """Récupère une tâche d'aubes par son ID."""
        return await self.aube_task_repo.get_by_id(task_id)

    async def list_aube_tasks(
        self,
        skip: int = 0,
        limit: int = 50,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[AubeTask], int]:
        """Liste les tâches d'aubes avec filtres."""
        return await self.aube_task_repo.list_tasks(
            skip=skip,
            limit=limit,
            task_type=task_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    async def update_aube_task(
        self,
        task_id: UUID,
        title: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        scheduled_date: Optional[datetime] = None,
        scheduled_time: Optional[str] = None,
        location: Optional[str] = None,
        aube_count: Optional[int] = None,
        aube_sizes: Optional[List[str]] = None,
        status: Optional[TaskStatus] = None,
        notes: Optional[str] = None,
    ) -> Optional[AubeTask]:
        """Met à jour une tâche d'aubes."""
        task = await self.aube_task_repo.get_by_id(task_id)
        if not task:
            return None

        # Mise à jour des champs
        if title is not None:
            task.title = title
        if task_type is not None:
            task.task_type = task_type
        if scheduled_date is not None:
            task.scheduled_date = scheduled_date
        if scheduled_time is not None:
            task.scheduled_time = scheduled_time
        if location is not None:
            task.location = location
        if aube_count is not None:
            task.aube_count = aube_count
        if aube_sizes is not None:
            task.aube_sizes = aube_sizes
        if status is not None:
            task.status = status
        if notes is not None:
            task.notes = notes

        return await self.aube_task_repo.update(task)

    async def complete_aube_task(
        self,
        task_id: UUID,
        photos_after: List[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[AubeTask]:
        """Marque une tâche d'aubes comme terminée."""
        task = await self.aube_task_repo.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.TERMINEE
        task.completed_at = utc_now()
        if photos_after:
            task.photos_after = photos_after
        if notes:
            task.notes = notes

        return await self.aube_task_repo.update(task)

    async def add_aube_task_photo(
        self,
        task_id: UUID,
        photo_url: str,
        phase: str,  # "before" | "after"
    ) -> Optional[AubeTask]:
        """Ajoute une photo avant ou après à une tâche d'aubes."""
        task = await self.aube_task_repo.get_by_id(task_id)
        if not task:
            return None
        if phase == "before":
            task.photos_before = list(task.photos_before or []) + [photo_url]
        else:
            task.photos_after = list(task.photos_after or []) + [photo_url]
        return await self.aube_task_repo.update(task)

    async def validate_aube_task(
        self,
        task_id: UUID,
        validated_by: UUID,
        notes: Optional[str] = None,
    ) -> Optional[AubeTask]:
        """Valide une tâche d'aubes terminée."""
        task = await self.aube_task_repo.get_by_id(task_id)
        if not task:
            return None

        if task.status != TaskStatus.TERMINEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task must be completed before validation",
            )

        task.status = TaskStatus.VALIDEE
        task.validated_at = utc_now()
        task.validated_by = validated_by
        if notes:
            task.notes = notes

        return await self.aube_task_repo.update(task)

    async def delete_aube_task(self, task_id: UUID) -> bool:
        """Supprime une tâche d'aubes."""
        return await self.aube_task_repo.delete(task_id)

    # ══════════════════════════════════════════════════════════════════
    #  HISTORIQUE DE MAINTENANCE
    # ══════════════════════════════════════════════════════════════════

    async def add_maintenance_history(
        self,
        item_id: UUID,
        maintenance_type: TaskType,
        description: str,
        performed_date: datetime,
        performed_by: UUID,
        cost: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[MaintenanceHistory]:
        """Ajoute un historique de maintenance."""
        # Vérifier que l'article existe
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            return None

        history = MaintenanceHistory(
            id=uuid4(),
            item_id=item_id,
            maintenance_type=maintenance_type,
            description=description,
            performed_date=performed_date,
            performed_by=performed_by,
            cost=cost,
            notes=notes,
        )

        # Mettre à jour la date de dernière maintenance de l'article
        item.last_maintenance_date = performed_date
        await self.item_repo.update(item)

        return await self.maintenance_repo.create(history)

    async def get_item_maintenance_history(
        self, item_id: UUID
    ) -> List[MaintenanceHistory]:
        """Récupère l'historique de maintenance d'un article."""
        return await self.maintenance_repo.get_by_item(item_id)

    # ══════════════════════════════════════════════════════════════════
    #  RAPPORTS ET STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def generate_material_report(
        self,
        start_date: datetime,
        end_date: datetime,
        generated_by: UUID,
    ) -> MaterialReport:
        """Génère un rapport de gestion du matériel."""
        # Récupérer tous les articles
        items, total_items = await self.item_repo.list_items(skip=0, limit=1000)

        # Répartition par catégorie
        items_by_category = {}
        for item in items:
            category = (
                item.category.value
                if hasattr(item.category, "value")
                else str(item.category)
            )
            items_by_category[category] = items_by_category.get(category, 0) + 1

        # Répartition par état
        items_by_condition = {}
        for item in items:
            condition = (
                item.condition.value
                if hasattr(item.condition, "value")
                else str(item.condition)
            )
            items_by_condition[condition] = items_by_condition.get(condition, 0) + 1

        # Récupérer toutes les tâches de la période
        cleaning_tasks, _ = await self.cleaning_task_repo.list_tasks(
            skip=0,
            limit=1000,
            start_date=start_date,
            end_date=end_date,
        )
        aube_tasks, _ = await self.aube_task_repo.list_tasks(
            skip=0,
            limit=1000,
            start_date=start_date,
            end_date=end_date,
        )

        total_tasks = len(cleaning_tasks) + len(aube_tasks)
        completed_tasks = sum(
            1
            for t in cleaning_tasks + aube_tasks
            if t.status in [TaskStatus.TERMINEE, TaskStatus.VALIDEE]
        )
        pending_tasks = sum(
            1 for t in cleaning_tasks + aube_tasks if t.status == TaskStatus.PLANIFIEE
        )

        # Coût total de maintenance
        total_maintenance_cost = await self.maintenance_repo.get_total_cost(
            start_date, end_date
        )

        # Articles nécessitant attention
        items_needing_attention = []
        for item in await self.item_repo.get_items_needing_maintenance():
            items_needing_attention.append(
                {
                    "id": str(item.id),
                    "name": item.name,
                    "condition": item.condition.value,
                    "reason": self._get_attention_reason(item),
                }
            )

        return MaterialReport(
            id=uuid4(),
            start_date=start_date,
            end_date=end_date,
            total_items=total_items,
            items_by_category=items_by_category,
            items_by_condition=items_by_condition,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            total_maintenance_cost=total_maintenance_cost,
            items_needing_attention=items_needing_attention,
            generated_by=generated_by,
        )

    def _get_attention_reason(self, item: MaterialItem) -> str:
        """Détermine la raison pour laquelle un article nécessite attention."""
        if item.condition == MaterialCondition.A_NETTOYER:
            return "À nettoyer"
        elif item.condition == MaterialCondition.A_REPARER:
            return "À réparer"
        elif item.condition == MaterialCondition.HORS_SERVICE:
            return "Hors service"
        elif item.next_maintenance_date and item.next_maintenance_date <= utc_now():
            return "Maintenance prévue dépassée"
        return "Nécessite attention"

    async def get_statistics(self) -> dict:
        """Récupère les statistiques globales."""
        # Récupérer tous les articles
        items, total_items = await self.item_repo.list_items(skip=0, limit=1000)

        # Répartition par catégorie
        items_by_category = {}
        for item in items:
            category = (
                item.category.value
                if hasattr(item.category, "value")
                else str(item.category)
            )
            items_by_category[category] = items_by_category.get(category, 0) + 1

        # Répartition par état
        items_by_condition = {}
        for item in items:
            condition = (
                item.condition.value
                if hasattr(item.condition, "value")
                else str(item.condition)
            )
            items_by_condition[condition] = items_by_condition.get(condition, 0) + 1

        # Articles nécessitant maintenance
        items_needing_maintenance = len(
            await self.item_repo.get_items_needing_maintenance()
        )

        # Récupérer toutes les tâches
        cleaning_tasks, _ = await self.cleaning_task_repo.list_tasks(skip=0, limit=1000)
        aube_tasks, _ = await self.aube_task_repo.list_tasks(skip=0, limit=1000)

        total_tasks = len(cleaning_tasks) + len(aube_tasks)
        completed_tasks = sum(
            1
            for t in cleaning_tasks + aube_tasks
            if t.status in [TaskStatus.TERMINEE, TaskStatus.VALIDEE]
        )
        pending_tasks = sum(
            1 for t in cleaning_tasks + aube_tasks if t.status == TaskStatus.PLANIFIEE
        )

        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        )

        return {
            "total_items": total_items,
            "items_by_category": items_by_category,
            "items_by_condition": items_by_condition,
            "items_needing_maintenance": items_needing_maintenance,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completion_rate,
        }
