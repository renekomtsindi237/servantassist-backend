"""
Service pour la gestion des formations liturgiques (CHARGE_LITURGIE).
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from src.core.entities.training import (
    MaterialType,
    ParticipationStatus,
    SessionMaterial,
    TrainingLevel,
    TrainingMaterial,
    TrainingParticipation,
    TrainingReport,
    TrainingSession,
    TrainingStats,
    TrainingStatus,
)
from src.core.interfaces.repositories import (
    ISessionMaterialRepository,
    ITrainingMaterialRepository,
    ITrainingParticipationRepository,
    ITrainingSessionRepository,
)
from src.core.utils import utc_now


class TrainingService:
    """Service de gestion des formations liturgiques."""

    def __init__(
        self,
        session_repo: ITrainingSessionRepository,
        participation_repo: ITrainingParticipationRepository,
        material_repo: ITrainingMaterialRepository,
        session_material_repo: ISessionMaterialRepository,
    ):
        self.session_repo = session_repo
        self.participation_repo = participation_repo
        self.material_repo = material_repo
        self.session_material_repo = session_material_repo

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES SESSIONS
    # ══════════════════════════════════════════════════════════════════

    async def create_session(
        self,
        title: str,
        description: str,
        level: TrainingLevel,
        date: datetime,
        start_time: str,
        end_time: str,
        duration_minutes: int,
        location: str,
        trainer_id: UUID,
        created_by: UUID,
        objectives: Optional[str] = None,
        max_participants: int = 0,
        materials_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> TrainingSession:
        """Crée une nouvelle session de formation."""
        training_session = TrainingSession(
            id=uuid4(),
            title=title,
            description=description,
            objectives=objectives,
            level=level,
            date=date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            location=location,
            trainer_id=trainer_id,
            max_participants=max_participants,
            status=TrainingStatus.PLANIFIEE,
            materials_url=materials_url,
            notes=notes,
            created_by=created_by,
        )

        session = await self.session_repo.create(training_session)
        return await self.session_repo.enrich_session(session)

    async def get_session(self, session_id: UUID) -> Optional[TrainingSession]:
        """Récupère une session par son ID."""
        session = await self.session_repo.get_by_id(session_id)
        if session:
            session = await self.session_repo.enrich_session(session)
        return session

    async def list_sessions(
        self,
        skip: int = 0,
        limit: int = 50,
        level: Optional[TrainingLevel] = None,
        status: Optional[TrainingStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        trainer_id: Optional[UUID] = None,
    ) -> Tuple[List[TrainingSession], int]:
        """Liste les sessions avec filtres."""
        sessions, total = await self.session_repo.list_sessions(
            skip=skip,
            limit=limit,
            level=level,
            status=status,
            start_date=start_date,
            end_date=end_date,
            trainer_id=trainer_id,
        )

        # Enrichir les sessions
        enriched_sessions = []
        for session in sessions:
            enriched_session = await self.session_repo.enrich_session(session)
            enriched_sessions.append(enriched_session)

        return enriched_sessions, total

    async def update_session(
        self,
        session_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        objectives: Optional[str] = None,
        level: Optional[TrainingLevel] = None,
        date: Optional[datetime] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        location: Optional[str] = None,
        trainer_id: Optional[UUID] = None,
        max_participants: Optional[int] = None,
        status: Optional[TrainingStatus] = None,
        materials_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[TrainingSession]:
        """Met à jour une session."""
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None

        # Mise à jour des champs
        if title is not None:
            session.title = title
        if description is not None:
            session.description = description
        if objectives is not None:
            session.objectives = objectives
        if level is not None:
            session.level = level
        if date is not None:
            session.date = date
        if start_time is not None:
            session.start_time = start_time
        if end_time is not None:
            session.end_time = end_time
        if duration_minutes is not None:
            session.duration_minutes = duration_minutes
        if location is not None:
            session.location = location
        if trainer_id is not None:
            session.trainer_id = trainer_id
        if max_participants is not None:
            session.max_participants = max_participants
        if status is not None:
            session.status = status
        if materials_url is not None:
            session.materials_url = materials_url
        if notes is not None:
            session.notes = notes

        updated_session = await self.session_repo.update(session)
        return await self.session_repo.enrich_session(updated_session)

    async def delete_session(self, session_id: UUID) -> bool:
        """Supprime une session."""
        # Vérifier qu'il n'y a pas de participations
        participations = await self.participation_repo.list_by_session(session_id)
        if participations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete session with participants. Cancel registrations first.",
            )

        return await self.session_repo.delete(session_id)

    async def get_my_sessions(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[TrainingSession], int]:
        """Récupère les sessions créées par un utilisateur."""
        sessions, total = await self.session_repo.get_by_created_by(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

        # Enrichir les sessions
        enriched_sessions = []
        for session in sessions:
            enriched_session = await self.session_repo.enrich_session(session)
            enriched_sessions.append(enriched_session)

        return enriched_sessions, total

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES PARTICIPATIONS
    # ══════════════════════════════════════════════════════════════════

    async def get_participation(self, participation_id: UUID) -> Optional[TrainingParticipation]:
        """Récupère une participation par son ID."""
        return await self.participation_repo.get_by_id(participation_id)

    async def register_participant(
        self,
        session_id: UUID,
        servant_id: UUID,
        registered_by: UUID,
        notes: Optional[str] = None,
    ) -> TrainingParticipation:
        """Inscrit un servant à une session."""
        # Vérifier que la session existe
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found.",
            )

        # Vérifier que la session n'est pas terminée ou annulée
        if session.status in [TrainingStatus.TERMINEE, TrainingStatus.ANNULEE]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot register for a session that is finished or cancelled.",
            )

        # Vérifier que le servant n'est pas déjà inscrit
        existing = await self.participation_repo.get_by_session_and_servant(session_id, servant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This servant is already registered for this training session.",
            )

        # Vérifier le nombre maximum de participants
        if session.max_participants > 0:
            participations = await self.participation_repo.list_by_session(session_id)
            if len(participations) >= session.max_participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Session is full",
                )

        participation = TrainingParticipation(
            id=uuid4(),
            session_id=session_id,
            servant_id=servant_id,
            status=ParticipationStatus.INSCRIT,
            notes=notes,
            registered_by=registered_by,
        )

        created = await self.participation_repo.create(participation)
        return await self.participation_repo.enrich_participation(created)

    async def register_participants_batch(
        self,
        session_id: UUID,
        servant_ids: List[UUID],
        registered_by: UUID,
        notes: Optional[str] = None,
    ) -> List[TrainingParticipation]:
        """Inscrit plusieurs servants à une session."""
        participations = []
        for servant_id in servant_ids:
            try:
                participation = await self.register_participant(
                    session_id=session_id,
                    servant_id=servant_id,
                    registered_by=registered_by,
                    notes=notes,
                )
                participations.append(participation)
            except HTTPException:
                # Ignorer les erreurs (déjà inscrit, etc.)
                continue

        return participations

    async def mark_attendance(
        self,
        participation_id: UUID,
        status: ParticipationStatus,
        marked_by: UUID,
        notes: Optional[str] = None,
    ) -> Optional[TrainingParticipation]:
        """Marque la présence d'un participant."""
        participation = await self.participation_repo.get_by_id(participation_id)
        if not participation:
            return None

        participation.status = status
        participation.attendance_marked_at = utc_now()
        participation.marked_by = marked_by
        if notes:
            participation.notes = notes

        updated = await self.participation_repo.update(participation)
        return await self.participation_repo.enrich_participation(updated)

    async def evaluate_participant(
        self,
        participation_id: UUID,
        evaluation_score: int,
        evaluation_comments: Optional[str] = None,
        certificate_issued: bool = False,
    ) -> Optional[TrainingParticipation]:
        """Évalue un participant."""
        participation = await self.participation_repo.get_by_id(participation_id)
        if not participation:
            return None

        participation.evaluation_score = evaluation_score
        participation.evaluation_comments = evaluation_comments
        participation.certificate_issued = certificate_issued

        if certificate_issued:
            participation.certificate_url = f"/api/v1/training/participations/{participation_id}/certificate"

        updated = await self.participation_repo.update(participation)
        return await self.participation_repo.enrich_participation(updated)

    async def get_session_participants(self, session_id: UUID) -> List[TrainingParticipation]:
        """Récupère les participants d'une session."""
        participations = await self.participation_repo.list_by_session(session_id)

        # Enrichir les participations
        enriched = []
        for participation in participations:
            enriched_participation = await self.participation_repo.enrich_participation(participation)
            enriched.append(enriched_participation)

        return enriched

    async def get_servant_participations(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TrainingParticipation]:
        """Récupère les participations d'un servant."""
        participations = await self.participation_repo.list_by_servant(servant_id, start_date, end_date)

        # Enrichir les participations
        enriched = []
        for participation in participations:
            enriched_participation = await self.participation_repo.enrich_participation(participation)
            enriched.append(enriched_participation)

        return enriched

    async def cancel_registration(self, participation_id: UUID) -> bool:
        """Annule une inscription."""
        return await self.participation_repo.delete(participation_id)

    async def get_servant_stats(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TrainingStats:
        """Récupère les statistiques d'un servant."""
        return await self.participation_repo.get_servant_stats(servant_id, start_date, end_date)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES MATÉRIELS
    # ══════════════════════════════════════════════════════════════════

    async def create_material(
        self,
        title: str,
        description: str,
        type: MaterialType,
        file_url: str,
        file_type: str,
        file_size: int,
        uploaded_by: UUID,
        thumbnail_url: Optional[str] = None,
        level: TrainingLevel = TrainingLevel.TOUS,
        tags: List[str] = None,
        is_public: bool = True,
    ) -> TrainingMaterial:
        """Crée un nouveau matériel pédagogique."""
        material = TrainingMaterial(
            id=uuid4(),
            title=title,
            description=description,
            type=type,
            file_url=file_url,
            file_type=file_type,
            file_size=file_size,
            thumbnail_url=thumbnail_url,
            level=level,
            tags=tags or [],
            is_public=is_public,
            uploaded_by=uploaded_by,
        )

        created = await self.material_repo.create(material)
        return await self.material_repo.enrich_material(created)

    async def get_material(self, material_id: UUID) -> Optional[TrainingMaterial]:
        """Récupère un matériel par son ID."""
        material = await self.material_repo.get_by_id(material_id)
        if material:
            # Incrémenter le compteur de vues
            await self.material_repo.increment_view_count(material_id)
            material = await self.material_repo.enrich_material(material)
        return material

    async def list_materials(
        self,
        skip: int = 0,
        limit: int = 50,
        type: Optional[MaterialType] = None,
        level: Optional[TrainingLevel] = None,
        is_public: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[TrainingMaterial], int]:
        """Liste les matériels avec filtres."""
        materials, total = await self.material_repo.list_materials(
            skip=skip,
            limit=limit,
            type=type,
            level=level,
            is_public=is_public,
            search=search,
        )

        # Enrichir les matériels
        enriched_materials = []
        for material in materials:
            enriched_material = await self.material_repo.enrich_material(material)
            enriched_materials.append(enriched_material)

        return enriched_materials, total

    async def update_material(
        self,
        material_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        type: Optional[MaterialType] = None,
        thumbnail_url: Optional[str] = None,
        level: Optional[TrainingLevel] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
    ) -> Optional[TrainingMaterial]:
        """Met à jour un matériel."""
        material = await self.material_repo.get_by_id(material_id)
        if not material:
            return None

        # Mise à jour des champs
        if title is not None:
            material.title = title
        if description is not None:
            material.description = description
        if type is not None:
            material.type = type
        if thumbnail_url is not None:
            material.thumbnail_url = thumbnail_url
        if level is not None:
            material.level = level
        if tags is not None:
            material.tags = tags
        if is_public is not None:
            material.is_public = is_public

        updated = await self.material_repo.update(material)
        return await self.material_repo.enrich_material(updated)

    async def delete_material(self, material_id: UUID) -> bool:
        """Supprime un matériel."""
        return await self.material_repo.delete(material_id)

    # ══════════════════════════════════════════════════════════════════
    #  ASSOCIATION SESSION-MATÉRIEL
    # ══════════════════════════════════════════════════════════════════

    async def add_material_to_session(
        self,
        session_id: UUID,
        material_id: UUID,
        order: int = 0,
        is_required: bool = False,
    ) -> SessionMaterial:
        """Ajoute un matériel à une session."""
        # Vérifier que la session existe
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cette session de formation est introuvable.",
            )

        # Vérifier que le matériel existe
        material = await self.material_repo.get_by_id(material_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ce support de formation est introuvable.",
            )

        session_material = SessionMaterial(
            id=uuid4(),
            session_id=session_id,
            material_id=material_id,
            order=order,
            is_required=is_required,
        )

        return await self.session_material_repo.create(session_material)

    async def get_session_materials(self, session_id: UUID) -> List[SessionMaterial]:
        """Récupère les matériels d'une session."""
        return await self.session_material_repo.get_by_session(session_id)

    async def remove_material_from_session(self, session_material_id: UUID) -> bool:
        """Retire un matériel d'une session."""
        return await self.session_material_repo.delete(session_material_id)

    # ══════════════════════════════════════════════════════════════════
    #  RAPPORTS ET STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def generate_training_report(
        self,
        start_date: datetime,
        end_date: datetime,
        generated_by: UUID,
        level: Optional[TrainingLevel] = None,
    ) -> TrainingReport:
        """Génère un rapport de formation."""
        # Récupérer toutes les sessions de la période
        sessions, total_sessions = await self.session_repo.list_sessions(
            skip=0,
            limit=1000,  # Pas de pagination pour le rapport
            level=level,
            start_date=start_date,
            end_date=end_date,
        )

        completed_sessions = sum(1 for s in sessions if s.status == TrainingStatus.TERMINEE)

        # Récupérer toutes les participations
        all_participations = []
        for session in sessions:
            participations = await self.participation_repo.list_by_session(session.id)
            all_participations.extend(participations)

        total_participants = len(all_participations)

        # Calculer le taux de présence moyen
        attended = sum(1 for p in all_participations if p.status == ParticipationStatus.PRESENT)
        average_attendance_rate = (attended / total_participants * 100) if total_participants > 0 else 0.0

        # Calculer la note moyenne
        scores = [p.evaluation_score for p in all_participations if p.evaluation_score is not None]
        average_evaluation_score = sum(scores) / len(scores) if scores else None

        # Compter les certificats
        certificates_issued = sum(1 for p in all_participations if p.certificate_issued)

        # Top performers (meilleurs participants)
        from collections import defaultdict

        user_stats: dict = defaultdict(lambda: {"scores": [], "attended": 0, "total": 0, "user_id": None})
        for p in all_participations:
            uid = str(p.user_id)
            user_stats[uid]["user_id"] = p.user_id
            user_stats[uid]["total"] += 1
            if p.status == ParticipationStatus.PRESENT:
                user_stats[uid]["attended"] += 1
            if p.evaluation_score is not None:
                user_stats[uid]["scores"].append(p.evaluation_score)

        top_performers = []
        for stats in user_stats.values():
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
            attendance_rate = stats["attended"] / stats["total"] * 100 if stats["total"] else 0.0
            top_performers.append(
                {
                    "user_id": str(stats["user_id"]),
                    "avg_score": round(avg_score, 2),
                    "attendance_rate": round(attendance_rate, 2),
                }
            )
        top_performers = sorted(top_performers, key=lambda x: x["avg_score"], reverse=True)[:10]

        # Répartition par niveau
        sessions_by_level = {}
        for session in sessions:
            level_str = session.level.value if hasattr(session.level, "value") else str(session.level)
            sessions_by_level[level_str] = sessions_by_level.get(level_str, 0) + 1

        return TrainingReport(
            id=uuid4(),
            start_date=start_date,
            end_date=end_date,
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            total_participants=total_participants,
            average_attendance_rate=average_attendance_rate,
            average_evaluation_score=average_evaluation_score,
            certificates_issued=certificates_issued,
            top_performers=top_performers,
            sessions_by_level=sessions_by_level,
            generated_by=generated_by,
        )
