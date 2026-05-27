"""
API endpoints pour le module INTENDANTS - Gestion du matériel.

Permissions:
- INTENDANT / INTENDANT_ADJOINT : Gestion complète
- Tous les utilisateurs authentifiés : Consultation
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.material_service import MaterialService
from src.core.entities.material import (
    MaterialCategory,
    MaterialCondition,
    TaskStatus,
    TaskType,
)
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.material_repository import (
    AubeTaskRepository,
    CleaningTaskRepository,
    MaintenanceHistoryRepository,
    MaterialItemRepository,
    TaskAssignmentRepository,
)
from src.infrastructure.services.storage_service import StorageService
from src.presentation.dependencies.auth_deps import get_current_user, require_intendant
from src.presentation.schemas.material import (
    AubeTaskComplete,
    AubeTaskCreate,
    AubeTaskListResponse,
    AubeTaskResponse,
    AubeTaskUpdate,
    CleaningTaskComplete,
    CleaningTaskCreate,
    CleaningTaskListResponse,
    CleaningTaskResponse,
    CleaningTaskUpdate,
    CleaningTaskValidate,
    MaintenanceHistoryCreate,
    MaintenanceHistoryResponse,
    MaterialItemCreate,
    MaterialItemListResponse,
    MaterialItemResponse,
    MaterialItemUpdate,
    MaterialReportRequest,
    MaterialReportResponse,
    MaterialStatsResponse,
    TaskAssignmentBatchCreate,
    TaskAssignmentCreate,
    TaskAssignmentResponse,
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  DÉPENDANCES
# ══════════════════════════════════════════════════════════════════


def get_material_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MaterialService:
    """Dépendance pour obtenir le service de matériel."""
    item_repo = MaterialItemRepository(db)
    cleaning_task_repo = CleaningTaskRepository(db)
    assignment_repo = TaskAssignmentRepository(db)
    aube_task_repo = AubeTaskRepository(db)
    maintenance_repo = MaintenanceHistoryRepository(db)
    return MaterialService(
        item_repo, cleaning_task_repo, assignment_repo, aube_task_repo, maintenance_repo
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - ARTICLES DE MATÉRIEL
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/items",
    response_model=MaterialItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un article",
    description="Crée un nouvel article de matériel (INTENDANT uniquement)",
)
async def create_material_item(
    data: MaterialItemCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Crée un nouvel article de matériel."""
    item = await service.create_item(
        name=data.name,
        category=data.category,
        quantity=data.quantity,
        location=data.location,
        created_by=current_user.id,
        description=data.description,
        size=data.size,
        condition=data.condition,
        purchase_date=data.purchase_date,
        notes=data.notes,
        photo_url=data.photo_url,
    )
    return item


@router.get(
    "/items",
    response_model=MaterialItemListResponse,
    summary="Liste des articles",
    description="Liste tous les articles de matériel avec filtres",
)
async def list_material_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[MaterialCategory] = None,
    condition: Optional[MaterialCondition] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Liste les articles de matériel."""
    items, total = await service.list_items(
        skip=skip,
        limit=limit,
        category=category,
        condition=condition,
        search=search,
    )
    return MaterialItemListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/items/{item_id}",
    response_model=MaterialItemResponse,
    summary="Détail d'un article",
    description="Récupère les détails d'un article de matériel",
)
async def get_material_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Récupère un article de matériel."""
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet article de matériel est introuvable.",
        )
    return item


@router.patch(
    "/items/{item_id}",
    response_model=MaterialItemResponse,
    summary="Modifier un article",
    description="Modifie un article de matériel (INTENDANT uniquement)",
)
async def update_material_item(
    item_id: UUID,
    data: MaterialItemUpdate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Modifie un article de matériel."""
    item = await service.update_item(
        item_id=item_id,
        name=data.name,
        category=data.category,
        description=data.description,
        quantity=data.quantity,
        size=data.size,
        condition=data.condition,
        location=data.location,
        purchase_date=data.purchase_date,
        last_maintenance_date=data.last_maintenance_date,
        next_maintenance_date=data.next_maintenance_date,
        notes=data.notes,
        photo_url=data.photo_url,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet article de matériel est introuvable.",
        )
    return item


@router.post(
    "/items/{item_id}/photo",
    response_model=MaterialItemResponse,
    summary="Photo d'un article",
    description="Upload ou remplace la photo d'un article de matériel (INTENDANT uniquement)",
)
async def upload_material_photo(
    item_id: UUID,
    file: Annotated[
        UploadFile, File(description="Photo de l'article (JPEG, PNG ou WebP, max 5 Mo)")
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """
    Upload ou remplace la photo d'un article de matériel.

    **Formats acceptés :** JPEG, PNG, WebP — **Taille max :** 5 Mo

    Si une photo existe déjà pour cet article, elle sera supprimée et remplacée.
    """
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article introuvable.",
        )

    storage = StorageService()
    file_data = await file.read()

    try:
        # Supprimer l'ancienne photo si elle existe
        if item.photo_url:
            await storage.delete_file(item.photo_url)

        photo_url = await storage.upload_material_photo(
            material_id=str(item_id),
            file_data=file_data,
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    updated = await service.update_item(item_id=item_id, photo_url=photo_url)
    return updated


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un article",
    description="Supprime un article de matériel (INTENDANT uniquement)",
)
async def delete_material_item(
    item_id: UUID,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Supprime un article de matériel."""
    success = await service.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet article de matériel est introuvable.",
        )


@router.get(
    "/items/maintenance/needed",
    response_model=MaterialItemListResponse,
    summary="Articles nécessitant maintenance",
    description="Liste les articles nécessitant une maintenance",
)
async def get_items_needing_maintenance(
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Liste les articles nécessitant maintenance."""
    items = await service.get_items_needing_maintenance()
    return MaterialItemListResponse(
        items=items,
        total=len(items),
        skip=0,
        limit=len(items),
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - TÂCHES DE NETTOYAGE
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/cleaning-tasks",
    response_model=CleaningTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une tâche de nettoyage",
    description="Crée une nouvelle tâche de nettoyage (INTENDANT uniquement)",
)
async def create_cleaning_task(
    data: CleaningTaskCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Crée une nouvelle tâche de nettoyage."""
    task = await service.create_cleaning_task(
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        location=data.location,
        created_by=current_user.id,
        items=data.items,
        notes=data.notes,
    )
    return task


@router.get(
    "/cleaning-tasks",
    response_model=CleaningTaskListResponse,
    summary="Liste des tâches",
    description="Liste toutes les tâches de nettoyage avec filtres",
)
async def list_cleaning_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    task_type: Optional[TaskType] = None,
    status: Optional[TaskStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Liste les tâches de nettoyage."""
    tasks, total = await service.list_cleaning_tasks(
        skip=skip,
        limit=limit,
        task_type=task_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    # Enrichir avec les assignations
    enriched_tasks = []
    for task in tasks:
        assignments = await service.get_task_assignments(task.id)
        task_dict = task.model_dump()
        task_dict["assigned_servants"] = [
            {
                "id": str(a.id),
                "servant_id": str(a.servant_id),
                "servant_name": a.servant_name,
            }
            for a in assignments
        ]
        enriched_tasks.append(CleaningTaskResponse(**task_dict))

    return CleaningTaskListResponse(
        items=enriched_tasks,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/cleaning-tasks/{task_id}",
    response_model=CleaningTaskResponse,
    summary="Détail d'une tâche",
    description="Récupère les détails d'une tâche de nettoyage",
)
async def get_cleaning_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Récupère une tâche de nettoyage."""
    task = await service.get_cleaning_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'entretien est introuvable.",
        )

    # Enrichir avec les assignations
    assignments = await service.get_task_assignments(task.id)
    task_dict = task.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]

    return CleaningTaskResponse(**task_dict)


@router.patch(
    "/cleaning-tasks/{task_id}",
    response_model=CleaningTaskResponse,
    summary="Modifier une tâche",
    description="Modifie une tâche de nettoyage (INTENDANT uniquement)",
)
async def update_cleaning_task(
    task_id: UUID,
    data: CleaningTaskUpdate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Modifie une tâche de nettoyage."""
    task = await service.update_cleaning_task(
        task_id=task_id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        location=data.location,
        items=data.items,
        status=data.status,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'entretien est introuvable.",
        )

    # Enrichir avec les assignations
    assignments = await service.get_task_assignments(task.id)
    task_dict = task.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]

    return CleaningTaskResponse(**task_dict)


@router.post(
    "/cleaning-tasks/{task_id}/complete",
    response_model=CleaningTaskResponse,
    summary="Marquer comme terminée",
    description="Marque une tâche comme terminée",
)
async def complete_cleaning_task(
    task_id: UUID,
    data: CleaningTaskComplete,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Marque une tâche comme terminée."""
    task = await service.complete_cleaning_task(
        task_id=task_id,
        photos_after=data.photos_after,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'entretien est introuvable.",
        )

    # Enrichir avec les assignations
    assignments = await service.get_task_assignments(task.id)
    task_dict = task.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]

    return CleaningTaskResponse(**task_dict)


@router.post(
    "/cleaning-tasks/{task_id}/validate",
    response_model=CleaningTaskResponse,
    summary="Valider une tâche",
    description="Valide une tâche terminée (INTENDANT uniquement)",
)
async def validate_cleaning_task(
    task_id: UUID,
    data: CleaningTaskValidate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Valide une tâche terminée."""
    task = await service.validate_cleaning_task(
        task_id=task_id,
        validated_by=current_user.id,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'entretien est introuvable.",
        )

    # Enrichir avec les assignations
    assignments = await service.get_task_assignments(task.id)
    task_dict = task.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]

    return CleaningTaskResponse(**task_dict)


@router.delete(
    "/cleaning-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une tâche",
    description="Supprime une tâche de nettoyage (INTENDANT uniquement)",
)
async def delete_cleaning_task(
    task_id: UUID,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Supprime une tâche de nettoyage."""
    success = await service.delete_cleaning_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'entretien est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - PHOTOS TÂCHES DE NETTOYAGE
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/cleaning-tasks/{task_id}/photos/before",
    response_model=CleaningTaskResponse,
    summary="Photo avant — tâche nettoyage",
    description="Ajoute une photo avant intervention. Format JPEG/PNG/WebP, max 5 Mo.",
)
async def upload_cleaning_task_photo_before(
    task_id: UUID,
    file: Annotated[
        UploadFile,
        File(description="Photo avant intervention (JPEG, PNG, WebP, max 5 Mo)"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    task = await service.get_cleaning_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable"
        )
    storage = StorageService()
    try:
        photo_url = await storage.upload_task_photo(
            task_id=str(task_id),
            file_data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await service.add_cleaning_task_photo(task_id, photo_url, phase="before")
    assignments = await service.get_task_assignments(updated.id)
    task_dict = updated.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]
    return CleaningTaskResponse(**task_dict)


@router.post(
    "/cleaning-tasks/{task_id}/photos/after",
    response_model=CleaningTaskResponse,
    summary="Photo après — tâche nettoyage",
    description="Ajoute une photo après intervention. Format JPEG/PNG/WebP, max 5 Mo.",
)
async def upload_cleaning_task_photo_after(
    task_id: UUID,
    file: Annotated[
        UploadFile,
        File(description="Photo après intervention (JPEG, PNG, WebP, max 5 Mo)"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    task = await service.get_cleaning_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable"
        )
    storage = StorageService()
    try:
        photo_url = await storage.upload_task_photo(
            task_id=str(task_id),
            file_data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await service.add_cleaning_task_photo(task_id, photo_url, phase="after")
    assignments = await service.get_task_assignments(updated.id)
    task_dict = updated.model_dump()
    task_dict["assigned_servants"] = [
        {
            "id": str(a.id),
            "servant_id": str(a.servant_id),
            "servant_name": a.servant_name,
        }
        for a in assignments
    ]
    return CleaningTaskResponse(**task_dict)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - ASSIGNATIONS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/cleaning-tasks/{task_id}/assign",
    response_model=TaskAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assigner un servant",
    description="Assigne un servant à une tâche (INTENDANT uniquement)",
)
async def assign_servant_to_task(
    task_id: UUID,
    data: TaskAssignmentCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Assigne un servant à une tâche."""
    assignment = await service.assign_servant_to_task(
        task_id=task_id,
        servant_id=data.servant_id,
        assigned_by=current_user.id,
    )
    return assignment


@router.post(
    "/cleaning-tasks/{task_id}/assign-batch",
    response_model=List[TaskAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assigner plusieurs servants",
    description="Assigne plusieurs servants à une tâche (INTENDANT uniquement)",
)
async def assign_servants_batch(
    task_id: UUID,
    data: TaskAssignmentBatchCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Assigne plusieurs servants à une tâche."""
    assignments = await service.assign_servants_batch(
        task_id=task_id,
        servant_ids=data.servant_ids,
        assigned_by=current_user.id,
    )
    return assignments


@router.get(
    "/servants/{servant_id}/assignments",
    response_model=List[TaskAssignmentResponse],
    summary="Assignations d'un servant",
    description="Liste les assignations d'un servant",
)
async def get_servant_assignments(
    servant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Liste les assignations d'un servant."""
    assignments = await service.get_servant_assignments(
        servant_id=servant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return assignments


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer une assignation",
    description="Retire une assignation (INTENDANT uniquement)",
)
async def remove_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Retire une assignation."""
    success = await service.remove_assignment(assignment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette affectation est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - TÂCHES D'AUBES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/aube-tasks",
    response_model=AubeTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une tâche d'aubes",
    description="Crée une nouvelle tâche de lavage/repassage d'aubes (INTENDANT uniquement)",
)
async def create_aube_task(
    data: AubeTaskCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Crée une nouvelle tâche d'aubes."""
    task = await service.create_aube_task(
        title=data.title,
        task_type=data.task_type,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        location=data.location,
        aube_count=data.aube_count,
        created_by=current_user.id,
        aube_sizes=data.aube_sizes,
        notes=data.notes,
        broadcast_notification=data.broadcast_notification,
    )
    return task


@router.get(
    "/aube-tasks",
    response_model=AubeTaskListResponse,
    summary="Liste des tâches d'aubes",
    description="Liste toutes les tâches d'aubes avec filtres",
)
async def list_aube_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    task_type: Optional[TaskType] = None,
    status: Optional[TaskStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Liste les tâches d'aubes."""
    tasks, total = await service.list_aube_tasks(
        skip=skip,
        limit=limit,
        task_type=task_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    return AubeTaskListResponse(
        items=tasks,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/aube-tasks/{task_id}",
    response_model=AubeTaskResponse,
    summary="Détail d'une tâche d'aubes",
    description="Récupère les détails d'une tâche d'aubes",
)
async def get_aube_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Récupère une tâche d'aubes."""
    task = await service.get_aube_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'aube est introuvable.",
        )
    return task


@router.patch(
    "/aube-tasks/{task_id}",
    response_model=AubeTaskResponse,
    summary="Modifier une tâche d'aubes",
    description="Modifie une tâche d'aubes (INTENDANT uniquement)",
)
async def update_aube_task(
    task_id: UUID,
    data: AubeTaskUpdate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Modifie une tâche d'aubes."""
    task = await service.update_aube_task(
        task_id=task_id,
        title=data.title,
        task_type=data.task_type,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        location=data.location,
        aube_count=data.aube_count,
        aube_sizes=data.aube_sizes,
        status=data.status,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'aube est introuvable.",
        )
    return task


@router.post(
    "/aube-tasks/{task_id}/complete",
    response_model=AubeTaskResponse,
    summary="Marquer comme terminée",
    description="Marque une tâche d'aubes comme terminée",
)
async def complete_aube_task(
    task_id: UUID,
    data: AubeTaskComplete,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Marque une tâche d'aubes comme terminée."""
    task = await service.complete_aube_task(
        task_id=task_id,
        photos_after=data.photos_after,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'aube est introuvable.",
        )
    return task


@router.post(
    "/aube-tasks/{task_id}/validate",
    response_model=AubeTaskResponse,
    summary="Valider une tâche d'aubes",
    description="Valide une tâche d'aubes terminée (INTENDANT uniquement)",
)
async def validate_aube_task(
    task_id: UUID,
    data: CleaningTaskValidate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Valide une tâche d'aubes terminée."""
    task = await service.validate_aube_task(
        task_id=task_id,
        validated_by=current_user.id,
        notes=data.notes,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'aube est introuvable.",
        )
    return task


@router.delete(
    "/aube-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une tâche d'aubes",
    description="Supprime une tâche d'aubes (INTENDANT uniquement)",
)
async def delete_aube_task(
    task_id: UUID,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Supprime une tâche d'aubes."""
    success = await service.delete_aube_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette tâche d'aube est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - PHOTOS TÂCHES D'AUBES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/aube-tasks/{task_id}/photos/before",
    response_model=AubeTaskResponse,
    summary="Photo avant — tâche d'aubes",
    description="Ajoute une photo avant intervention. Format JPEG/PNG/WebP, max 5 Mo.",
)
async def upload_aube_task_photo_before(
    task_id: UUID,
    file: Annotated[
        UploadFile,
        File(description="Photo avant intervention (JPEG, PNG, WebP, max 5 Mo)"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    task = await service.get_aube_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable"
        )
    storage = StorageService()
    try:
        photo_url = await storage.upload_task_photo(
            task_id=str(task_id),
            file_data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await service.add_aube_task_photo(task_id, photo_url, phase="before")
    return updated


@router.post(
    "/aube-tasks/{task_id}/photos/after",
    response_model=AubeTaskResponse,
    summary="Photo après — tâche d'aubes",
    description="Ajoute une photo après intervention. Format JPEG/PNG/WebP, max 5 Mo.",
)
async def upload_aube_task_photo_after(
    task_id: UUID,
    file: Annotated[
        UploadFile,
        File(description="Photo après intervention (JPEG, PNG, WebP, max 5 Mo)"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    task = await service.get_aube_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable"
        )
    storage = StorageService()
    try:
        photo_url = await storage.upload_task_photo(
            task_id=str(task_id),
            file_data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    updated = await service.add_aube_task_photo(task_id, photo_url, phase="after")
    return updated


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - HISTORIQUE DE MAINTENANCE
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/items/{item_id}/maintenance",
    response_model=MaintenanceHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un historique",
    description="Ajoute un historique de maintenance (INTENDANT uniquement)",
)
async def add_maintenance_history(
    item_id: UUID,
    data: MaintenanceHistoryCreate,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Ajoute un historique de maintenance."""
    history = await service.add_maintenance_history(
        item_id=item_id,
        maintenance_type=data.maintenance_type,
        description=data.description,
        performed_date=data.performed_date,
        performed_by=current_user.id,
        cost=data.cost,
        notes=data.notes,
    )
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet article de matériel est introuvable.",
        )
    return history


@router.get(
    "/items/{item_id}/maintenance",
    response_model=List[MaintenanceHistoryResponse],
    summary="Historique de maintenance",
    description="Récupère l'historique de maintenance d'un article",
)
async def get_item_maintenance_history(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Récupère l'historique de maintenance d'un article."""
    history = await service.get_item_maintenance_history(item_id)
    return history


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - RAPPORTS ET STATISTIQUES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/report",
    response_model=MaterialReportResponse,
    summary="Générer un rapport",
    description="Génère un rapport de gestion du matériel (INTENDANT uniquement)",
)
async def generate_material_report(
    data: MaterialReportRequest,
    current_user: User = Depends(require_intendant),
    service: MaterialService = Depends(get_material_service),
):
    """Génère un rapport de gestion du matériel."""
    report = await service.generate_material_report(
        start_date=data.start_date,
        end_date=data.end_date,
        generated_by=current_user.id,
    )
    return report


@router.get(
    "/stats",
    response_model=MaterialStatsResponse,
    summary="Statistiques globales",
    description="Récupère les statistiques globales de gestion du matériel",
)
async def get_material_stats(
    current_user: User = Depends(get_current_user),
    service: MaterialService = Depends(get_material_service),
):
    """Récupère les statistiques globales."""
    stats = await service.get_statistics()
    return MaterialStatsResponse(**stats)
