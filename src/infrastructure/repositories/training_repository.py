"""
Repository pour la gestion des formations liturgiques (CHARGE_LITURGIE).
"""
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.training import (
    MaterialType,
    ParticipationStatus,
    SessionMaterial,
    TrainingLevel,
    TrainingMaterial,
    TrainingParticipation,
    TrainingSession,
    TrainingStats,
    TrainingStatus,
)
from src.core.entities.user import User, UserRole
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name")


class TrainingSessionRepository:
    """Repository pour les sessions de formation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, training_session: TrainingSession) -> TrainingSession:
        """Crée une nouvelle session de formation."""
        self.session.add(training_session)
        await self.session.commit()
        await self.session.refresh(training_session)
        return training_session

    async def get_by_id(self, session_id: UUID) -> Optional[TrainingSession]:
        """Récupère une session par son ID."""
        result = await self.session.execute(
            select(TrainingSession).where(TrainingSession.id == session_id)
        )
        return result.scalar_one_or_none()

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
        query = select(TrainingSession)

        # Filtres
        if level:
            query = query.where(TrainingSession.level == level)
        if status:
            query = query.where(TrainingSession.status == status)
        if start_date:
            query = query.where(TrainingSession.date >= start_date)
        if end_date:
            query = query.where(TrainingSession.date <= end_date)
        if trainer_id:
            query = query.where(TrainingSession.trainer_id == trainer_id)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(TrainingSession.date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        sessions = list(result.scalars().all())

        return sessions, total

    async def update(self, training_session: TrainingSession) -> TrainingSession:
        """Met à jour une session."""
        training_session.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(training_session)
        return training_session

    async def delete(self, session_id: UUID) -> bool:
        """Supprime une session."""
        training_session = await self.get_by_id(session_id)
        if not training_session:
            return False

        await self.session.delete(training_session)
        await self.session.commit()
        return True

    async def get_by_created_by(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[TrainingSession], int]:
        """Récupère les sessions créées par un utilisateur."""
        query = select(TrainingSession).where(TrainingSession.created_by == user_id)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(TrainingSession.date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        sessions = list(result.scalars().all())

        return sessions, total

    async def enrich_session(
        self, training_session: TrainingSession
    ) -> TrainingSession:
        """Enrichit une session avec les noms."""
        # Récupérer le nom du formateur
        trainer_result = await self.session.execute(
            select(User).where(User.id == training_session.trainer_id)
        )
        trainer = trainer_result.scalar_one_or_none()
        if trainer:
            decrypt_str_fields(trainer, _USER_PII)
            training_session.trainer_name = f"{trainer.first_name} {trainer.last_name}"

        # Compter les participants
        count_result = await self.session.execute(
            select(func.count()).where(
                TrainingParticipation.session_id == training_session.id
            )
        )
        training_session.current_participants = count_result.scalar() or 0

        return training_session


class TrainingParticipationRepository:
    """Repository pour les participations aux formations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, participation: TrainingParticipation
    ) -> TrainingParticipation:
        """Crée une nouvelle participation."""
        self.session.add(participation)
        await self.session.commit()
        await self.session.refresh(participation)
        return participation

    async def create_batch(
        self, participations: List[TrainingParticipation]
    ) -> List[TrainingParticipation]:
        """Crée plusieurs participations en batch."""
        for participation in participations:
            self.session.add(participation)
        await self.session.commit()
        for participation in participations:
            await self.session.refresh(participation)
        return participations

    async def get_by_id(
        self, participation_id: UUID
    ) -> Optional[TrainingParticipation]:
        """Récupère une participation par son ID."""
        result = await self.session.execute(
            select(TrainingParticipation).where(
                TrainingParticipation.id == participation_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_session_and_servant(
        self, session_id: UUID, servant_id: UUID
    ) -> Optional[TrainingParticipation]:
        """Récupère une participation par session et servant."""
        result = await self.session.execute(
            select(TrainingParticipation).where(
                and_(
                    TrainingParticipation.session_id == session_id,
                    TrainingParticipation.servant_id == servant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: UUID) -> List[TrainingParticipation]:
        """Liste les participations d'une session."""
        result = await self.session.execute(
            select(TrainingParticipation)
            .where(TrainingParticipation.session_id == session_id)
            .order_by(TrainingParticipation.registration_date)
        )
        return list(result.scalars().all())

    async def list_by_servant(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TrainingParticipation]:
        """Liste les participations d'un servant."""
        # Joindre avec les sessions pour filtrer par date
        query = (
            select(TrainingParticipation)
            .join(
                TrainingSession, TrainingParticipation.session_id == TrainingSession.id
            )
            .where(TrainingParticipation.servant_id == servant_id)
        )

        if start_date:
            query = query.where(TrainingSession.date >= start_date)
        if end_date:
            query = query.where(TrainingSession.date <= end_date)

        query = query.order_by(TrainingSession.date.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, participation: TrainingParticipation
    ) -> TrainingParticipation:
        """Met à jour une participation."""
        participation.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(participation)
        return participation

    async def delete(self, participation_id: UUID) -> bool:
        """Supprime une participation."""
        participation = await self.get_by_id(participation_id)
        if not participation:
            return False

        await self.session.delete(participation)
        await self.session.commit()
        return True

    async def get_servant_stats(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TrainingStats:
        """Calcule les statistiques d'un servant."""
        # Récupérer le servant
        servant_result = await self.session.execute(
            select(User).where(User.id == servant_id)
        )
        servant = servant_result.scalar_one_or_none()
        if not servant:
            raise ValueError("Servant not found")
        decrypt_str_fields(servant, _USER_PII)

        # Récupérer toutes les participations
        participations = await self.list_by_servant(servant_id, start_date, end_date)

        total_sessions = len(participations)
        attended_sessions = sum(
            1 for p in participations if p.status == ParticipationStatus.PRESENT
        )
        absent_sessions = sum(
            1
            for p in participations
            if p.status in [ParticipationStatus.ABSENT, ParticipationStatus.EXCUSE]
        )

        attendance_rate = (
            (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
        )

        # Calculer la note moyenne
        scores = [
            p.evaluation_score for p in participations if p.evaluation_score is not None
        ]
        average_score = sum(scores) / len(scores) if scores else None

        # Compter les certificats
        certificates_earned = sum(1 for p in participations if p.certificate_issued)

        # Dernière formation
        last_training_date = None
        if participations:
            # Récupérer la session la plus récente
            last_participation = participations[0]  # Déjà trié par date desc
            session_result = await self.session.execute(
                select(TrainingSession).where(
                    TrainingSession.id == last_participation.session_id
                )
            )
            last_session = session_result.scalar_one_or_none()
            if last_session:
                last_training_date = last_session.date

        return TrainingStats(
            servant_id=servant_id,
            servant_name=f"{servant.first_name} {servant.last_name}",
            total_sessions=total_sessions,
            attended_sessions=attended_sessions,
            absent_sessions=absent_sessions,
            attendance_rate=attendance_rate,
            average_score=average_score,
            certificates_earned=certificates_earned,
            last_training_date=last_training_date,
        )

    async def enrich_participation(
        self, participation: TrainingParticipation
    ) -> TrainingParticipation:
        """Enrichit une participation avec les noms."""
        # Récupérer le nom du servant
        servant_result = await self.session.execute(
            select(User).where(User.id == participation.servant_id)
        )
        servant = servant_result.scalar_one_or_none()
        if servant:
            decrypt_str_fields(servant, _USER_PII)
            participation.servant_name = f"{servant.first_name} {servant.last_name}"

        return participation


class TrainingMaterialRepository:
    """Repository pour les matériels pédagogiques."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, material: TrainingMaterial) -> TrainingMaterial:
        """Crée un nouveau matériel."""
        self.session.add(material)
        await self.session.commit()
        await self.session.refresh(material)
        return material

    async def get_by_id(self, material_id: UUID) -> Optional[TrainingMaterial]:
        """Récupère un matériel par son ID."""
        result = await self.session.execute(
            select(TrainingMaterial).where(TrainingMaterial.id == material_id)
        )
        return result.scalar_one_or_none()

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
        query = select(TrainingMaterial)

        # Filtres
        if type:
            query = query.where(TrainingMaterial.type == type)
        if level:
            query = query.where(TrainingMaterial.level == level)
        if is_public is not None:
            query = query.where(TrainingMaterial.is_public == is_public)
        if search:
            query = query.where(
                TrainingMaterial.title.ilike(f"%{search}%")
                | TrainingMaterial.description.ilike(f"%{search}%")
            )

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(TrainingMaterial.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        materials = list(result.scalars().all())

        return materials, total

    async def update(self, material: TrainingMaterial) -> TrainingMaterial:
        """Met à jour un matériel."""
        material.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(material)
        return material

    async def delete(self, material_id: UUID) -> bool:
        """Supprime un matériel."""
        material = await self.get_by_id(material_id)
        if not material:
            return False

        await self.session.delete(material)
        await self.session.commit()
        return True

    async def increment_view_count(self, material_id: UUID) -> bool:
        """Incrémente le compteur de vues."""
        material = await self.get_by_id(material_id)
        if not material:
            return False

        material.view_count += 1
        await self.session.commit()
        return True

    async def enrich_material(self, material: TrainingMaterial) -> TrainingMaterial:
        """Enrichit un matériel avec les noms."""
        # Récupérer le nom de l'uploader
        uploader_result = await self.session.execute(
            select(User).where(User.id == material.uploaded_by)
        )
        uploader = uploader_result.scalar_one_or_none()
        if uploader:
            decrypt_str_fields(uploader, _USER_PII)
            material.uploaded_by_name = f"{uploader.first_name} {uploader.last_name}"

        return material


class SessionMaterialRepository:
    """Repository pour les associations session-matériel."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, session_material: SessionMaterial) -> SessionMaterial:
        """Crée une nouvelle association."""
        self.session.add(session_material)
        await self.session.commit()
        await self.session.refresh(session_material)
        return session_material

    async def get_by_session(self, session_id: UUID) -> List[SessionMaterial]:
        """Récupère les matériels d'une session."""
        result = await self.session.execute(
            select(SessionMaterial)
            .where(SessionMaterial.session_id == session_id)
            .order_by(SessionMaterial.order)
        )
        return list(result.scalars().all())

    async def delete(self, session_material_id: UUID) -> bool:
        """Supprime une association."""
        result = await self.session.execute(
            select(SessionMaterial).where(SessionMaterial.id == session_material_id)
        )
        session_material = result.scalar_one_or_none()
        if not session_material:
            return False

        await self.session.delete(session_material)
        await self.session.commit()
        return True
