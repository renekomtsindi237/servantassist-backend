"""
API endpoints pour le module CHARGE_LITURGIE - Formations liturgiques.

Permissions:
- CHARGE_LITURGIE / CHARGE_LITURGIE_ADJOINT : Gestion complète
- Tous les utilisateurs authentifiés : Consultation et participation
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.training_service import TrainingService
from src.core.entities.training import MaterialType, ParticipationStatus, TrainingLevel, TrainingStatus
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.training_repository import (
    SessionMaterialRepository,
    TrainingMaterialRepository,
    TrainingParticipationRepository,
    TrainingSessionRepository,
)
from src.infrastructure.services.storage_service import StorageService
from src.presentation.dependencies.auth_deps import get_current_user, require_charge_liturgie
from src.presentation.schemas.training import (
    SessionMaterialAdd,
    SessionMaterialResponse,
    TrainingMaterialCreate,
    TrainingMaterialListResponse,
    TrainingMaterialResponse,
    TrainingMaterialUpdate,
    TrainingParticipationBatchCreate,
    TrainingParticipationCreate,
    TrainingParticipationEvaluate,
    TrainingParticipationListResponse,
    TrainingParticipationMarkAttendance,
    TrainingParticipationResponse,
    TrainingReportRequest,
    TrainingReportResponse,
    TrainingSessionCreate,
    TrainingSessionListResponse,
    TrainingSessionResponse,
    TrainingSessionUpdate,
    TrainingStatsResponse,
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  DÉPENDANCES
# ══════════════════════════════════════════════════════════════════


def get_training_service(db: Annotated[AsyncSession, Depends(
    get_db_session)]) -> TrainingService:
    """Dépendance pour obtenir le service de formation."""
    session_repo = TrainingSessionRepository(db)
    participation_repo = TrainingParticipationRepository(db)
    material_repo = TrainingMaterialRepository(db)
    session_material_repo = SessionMaterialRepository(db)
    return TrainingService(session_repo, participation_repo,
                           material_repo, session_material_repo)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - SESSIONS DE FORMATION
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/sessions",
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une session de formation",
    description="Crée une nouvelle session de formation (CHARGE_LITURGIE uniquement)",
)
async def create_training_session(
    data: TrainingSessionCreate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Crée une nouvelle session de formation."""
    session = await service.create_session(
        title=data.title,
        description=data.description,
        objectives=data.objectives,
        level=data.level,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_minutes=data.duration_minutes,
        location=data.location,
        trainer_id=data.trainer_id,
        max_participants=data.max_participants,
        materials_url=data.materials_url,
        notes=data.notes,
        created_by=current_user.id,
    )
    return session


@router.get(
    "/sessions",
    response_model=TrainingSessionListResponse,
    summary="Liste des sessions",
    description="Liste toutes les sessions de formation avec filtres",
)
async def list_training_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    level: Optional[TrainingLevel] = None,
    status: Optional[TrainingStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    trainer_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Liste les sessions de formation."""
    sessions, total = await service.list_sessions(
        skip=skip,
        limit=limit,
        level=level,
        status=status,
        start_date=start_date,
        end_date=end_date,
        trainer_id=trainer_id,
    )
    return TrainingSessionListResponse(
        items=sessions,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=TrainingSessionResponse,
    summary="Détail d'une session",
    description="Récupère les détails d'une session de formation",
)
async def get_training_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Récupère une session de formation."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette session de formation est introuvable.",
        )
    return session


@router.patch(
    "/sessions/{session_id}",
    response_model=TrainingSessionResponse,
    summary="Modifier une session",
    description="Modifie une session de formation (CHARGE_LITURGIE uniquement)",
)
async def update_training_session(
    session_id: UUID,
    data: TrainingSessionUpdate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Modifie une session de formation."""
    session = await service.update_session(
        session_id=session_id,
        title=data.title,
        description=data.description,
        objectives=data.objectives,
        level=data.level,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_minutes=data.duration_minutes,
        location=data.location,
        trainer_id=data.trainer_id,
        max_participants=data.max_participants,
        status=data.status,
        materials_url=data.materials_url,
        notes=data.notes,
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette session de formation est introuvable.",
        )
    return session


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une session",
    description="Supprime une session de formation (CHARGE_LITURGIE uniquement)",
)
async def delete_training_session(
    session_id: UUID,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Supprime une session de formation."""
    success = await service.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette session de formation est introuvable.",
        )


@router.get(
    "/sessions/me/list",
    response_model=TrainingSessionListResponse,
    summary="Mes sessions",
    description="Récupère les sessions créées par l'utilisateur connecté",
)
async def get_my_training_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Récupère les sessions créées par l'utilisateur."""
    sessions, total = await service.get_my_sessions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return TrainingSessionListResponse(
        items=sessions,
        total=total,
        skip=skip,
        limit=limit,
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - PARTICIPATIONS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/sessions/{session_id}/register",
    response_model=TrainingParticipationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="S'inscrire à une session",
    description="Inscrit un servant à une session de formation",
)
async def register_to_session(
    session_id: UUID,
    data: TrainingParticipationCreate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Inscrit un servant à une session."""
    participation = await service.register_participant(
        session_id=session_id,
        servant_id=data.servant_id,
        registered_by=current_user.id,
        notes=data.notes,
    )
    return participation


@router.post(
    "/sessions/{session_id}/register-batch",
    response_model=TrainingParticipationListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrire plusieurs servants",
    description="Inscrit plusieurs servants à une session (CHARGE_LITURGIE uniquement)",
)
async def register_batch_to_session(
    session_id: UUID,
    data: TrainingParticipationBatchCreate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Inscrit plusieurs servants à une session."""
    participations = await service.register_participants_batch(
        session_id=session_id,
        servant_ids=data.servant_ids,
        registered_by=current_user.id,
        notes=data.notes,
    )
    return TrainingParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.get(
    "/sessions/{session_id}/participants",
    response_model=TrainingParticipationListResponse,
    summary="Participants d'une session",
    description="Liste les participants d'une session",
)
async def get_session_participants(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Liste les participants d'une session."""
    participations = await service.get_session_participants(session_id)
    return TrainingParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.post(
    "/participations/{participation_id}/attendance",
    response_model=TrainingParticipationResponse,
    summary="Marquer la présence",
    description="Marque la présence d'un participant (CHARGE_LITURGIE uniquement)",
)
async def mark_participant_attendance(
    participation_id: UUID,
    data: TrainingParticipationMarkAttendance,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Marque la présence d'un participant."""
    participation = await service.mark_attendance(
        participation_id=participation_id,
        status=data.status,
        marked_by=current_user.id,
        notes=data.notes,
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )
    return participation


@router.post(
    "/participations/{participation_id}/evaluate",
    response_model=TrainingParticipationResponse,
    summary="Évaluer un participant",
    description="Évalue un participant (CHARGE_LITURGIE uniquement)",
)
async def evaluate_participant(
    participation_id: UUID,
    data: TrainingParticipationEvaluate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Évalue un participant."""
    participation = await service.evaluate_participant(
        participation_id=participation_id,
        evaluation_score=data.evaluation_score,
        evaluation_comments=data.evaluation_comments,
        certificate_issued=data.certificate_issued,
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )
    return participation


@router.delete(
    "/participations/{participation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler une inscription",
    description="Annule l'inscription d'un participant (CHARGE_LITURGIE uniquement)",
)
async def cancel_participation(
    participation_id: UUID,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Annule une inscription."""
    success = await service.cancel_registration(participation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )


@router.get(
    "/servants/{servant_id}/participations",
    response_model=TrainingParticipationListResponse,
    summary="Participations d'un servant",
    description="Liste les participations d'un servant",
)
async def get_servant_participations(
    servant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Liste les participations d'un servant."""
    participations = await service.get_servant_participations(
        servant_id=servant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return TrainingParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.get(
    "/servants/{servant_id}/stats",
    response_model=TrainingStatsResponse,
    summary="Statistiques d'un servant",
    description="Récupère les statistiques de formation d'un servant",
)
async def get_servant_training_stats(
    servant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Récupère les statistiques d'un servant."""
    stats = await service.get_servant_stats(
        servant_id=servant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return stats


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - MATÉRIELS PÉDAGOGIQUES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/materials/upload",
    response_model=TrainingMaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload d'un matériel pédagogique",
    description=(
        "Upload multipart d'un fichier pédagogique (CHARGE_LITURGIE uniquement). "
        "Routage automatique : image → images/training/, document → documents/training/. "
        "Max 10 Mo."
    ),
)
async def upload_training_material(
    file: Annotated[UploadFile, File(description="Fichier pédagogique (PDF, DOC, DOCX, image, max 10 Mo)")],
    title: str = Form(...),
    description: str = Form(...),
    type: MaterialType = Form(...),
    level: TrainingLevel = Form(TrainingLevel.TOUS),
    is_public: bool = Form(True),
    tags: Optional[str] = Form(None, description="Tags séparés par des virgules"),
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Upload un fichier et crée le matériel pédagogique associé."""
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    storage = StorageService()
    try:
        file_url = await storage.upload_training_material(
            training_id=str(current_user.id),
            file_data=file_data,
            content_type=content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    tags_list = [t.strip() for t in tags.split(",")] if tags else []
    material = await service.create_material(
        title=title,
        description=description,
        type=type,
        file_url=file_url,
        file_type=content_type,
        file_size=len(file_data),
        level=level,
        tags=tags_list,
        is_public=is_public,
        uploaded_by=current_user.id,
    )
    return material


@router.post(
    "/materials",
    response_model=TrainingMaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un matériel",
    description="Crée un nouveau matériel pédagogique (CHARGE_LITURGIE uniquement)",
)
async def create_training_material(
    data: TrainingMaterialCreate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Crée un nouveau matériel pédagogique."""
    material = await service.create_material(
        title=data.title,
        description=data.description,
        type=data.type,
        file_url=data.file_url,
        file_type=data.file_type,
        file_size=data.file_size,
        thumbnail_url=data.thumbnail_url,
        level=data.level,
        tags=data.tags,
        is_public=data.is_public,
        uploaded_by=current_user.id,
    )
    return material


@router.get(
    "/materials",
    response_model=TrainingMaterialListResponse,
    summary="Liste des matériels",
    description="Liste tous les matériels pédagogiques (bibliothèque)",
)
async def list_training_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    type: Optional[MaterialType] = None,
    level: Optional[TrainingLevel] = None,
    is_public: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Liste les matériels pédagogiques."""
    materials, total = await service.list_materials(
        skip=skip,
        limit=limit,
        type=type,
        level=level,
        is_public=is_public,
        search=search,
    )
    return TrainingMaterialListResponse(
        items=materials,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/materials/{material_id}",
    response_model=TrainingMaterialResponse,
    summary="Détail d'un matériel",
    description="Récupère les détails d'un matériel pédagogique",
)
async def get_training_material(
    material_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Récupère un matériel pédagogique."""
    material = await service.get_material(material_id)
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce support de formation est introuvable.",
        )
    return material


@router.patch(
    "/materials/{material_id}",
    response_model=TrainingMaterialResponse,
    summary="Modifier un matériel",
    description="Modifie un matériel pédagogique (CHARGE_LITURGIE uniquement)",
)
async def update_training_material(
    material_id: UUID,
    data: TrainingMaterialUpdate,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Modifie un matériel pédagogique."""
    material = await service.update_material(
        material_id=material_id,
        title=data.title,
        description=data.description,
        type=data.type,
        thumbnail_url=data.thumbnail_url,
        level=data.level,
        tags=data.tags,
        is_public=data.is_public,
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce support de formation est introuvable.",
        )
    return material


@router.delete(
    "/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un matériel",
    description="Supprime un matériel pédagogique (CHARGE_LITURGIE uniquement)",
)
async def delete_training_material(
    material_id: UUID,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Supprime un matériel pédagogique."""
    success = await service.delete_material(material_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce support de formation est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - RAPPORTS
# ══════════════════════════════════════════════════════════════════


@router.get(
    "/participations/{participation_id}/certificate",
    summary="Télécharger le certificat PDF",
    description="Génère et retourne le certificat de formation en PDF.",
)
async def download_certificate(
    participation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Génère le certificat PDF pour une participation validée."""
    participation = await service.get_participation(participation_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation introuvable.",
        )
    if not participation.certificate_issued:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun certificat n'a encore été délivré pour cette participation.",
        )

    # Récupérer la session de formation pour le titre
    session = await service.get_session(participation.session_id)
    session_title = session.title if session else "Formation"
    session_date = session.date if session and hasattr(session, "date") else participation.created_at

    from src.infrastructure.services.pdf_service import PDFService

    pdf_svc = PDFService()
    pdf_bytes = pdf_svc.generate_certificate(
        participant_first_name=str(participation.user_id),  # enrichi si user chargé
        participant_last_name="",
        training_title=session_title,
        training_date=session_date,
        score=float(participation.evaluation_score) if participation.evaluation_score else None,
    )
    filename = f"certificat_{participation_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/report",
    response_model=TrainingReportResponse,
    summary="Générer un rapport",
    description="Génère un rapport de formation (CHARGE_LITURGIE uniquement)",
)
async def generate_training_report(
    data: TrainingReportRequest,
    current_user: User = Depends(require_charge_liturgie),
    service: TrainingService = Depends(get_training_service),
):
    """Génère un rapport de formation."""
    report = await service.generate_training_report(
        start_date=data.start_date,
        end_date=data.end_date,
        generated_by=current_user.id,
        level=data.level,
    )
    return report
