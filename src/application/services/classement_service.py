"""
Service pour la gestion des classements.
"""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from src.core.entities.classement import Classement, ClassementStatus, ClassementType
from src.core.utils import utc_now
from src.infrastructure.repositories.classement_repository import ClassementRepository


class ClassementService:
    def __init__(self, repo: ClassementRepository):
        self.repo = repo

    async def create(
        self,
        type: ClassementType,
        date,
        heure: str,
        lieu: str,
        created_by: UUID,
        solennite: Optional[str] = None,
        couleur_liturgique: Optional[str] = None,
        semaine: Optional[int] = None,
        annee: Optional[int] = None,
        horaire: Optional[str] = None,
        type_extra: Optional[str] = None,
        participants: Optional[str] = None,
        postes: Optional[List[Dict[str, Any]]] = None,
    ) -> Classement:
        now = utc_now()
        classement = Classement(
            id=uuid4(),
            type=type,
            status=ClassementStatus.BROUILLON,
            date=date,
            heure=heure,
            lieu=lieu,
            solennite=solennite,
            couleur_liturgique=couleur_liturgique,
            semaine=semaine,
            annee=annee,
            horaire=horaire,
            type_extra=type_extra,
            participants=participants,
            postes=postes or [],
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        return await self.repo.create(classement)

    async def get(self, classement_id: UUID) -> Optional[Classement]:
        return await self.repo.get_by_id(classement_id)

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        type: Optional[ClassementType] = None,
        status: Optional[ClassementStatus] = None,
        created_by: Optional[UUID] = None,
    ) -> Tuple[List[Classement], int]:
        return await self.repo.list(skip=skip, limit=limit, type=type, status=status, created_by=created_by)

    async def update(
        self,
        classement_id: UUID,
        date=None,
        heure: Optional[str] = None,
        lieu: Optional[str] = None,
        solennite: Optional[str] = None,
        couleur_liturgique: Optional[str] = None,
        semaine: Optional[int] = None,
        annee: Optional[int] = None,
        horaire: Optional[str] = None,
        type_extra: Optional[str] = None,
        participants: Optional[str] = None,
        postes: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Classement]:
        classement = await self.repo.get_by_id(classement_id)
        if not classement:
            return None

        if date is not None:
            classement.date = date
        if heure is not None:
            classement.heure = heure
        if lieu is not None:
            classement.lieu = lieu
        if solennite is not None:
            classement.solennite = solennite
        if couleur_liturgique is not None:
            classement.couleur_liturgique = couleur_liturgique
        if semaine is not None:
            classement.semaine = semaine
        if annee is not None:
            classement.annee = annee
        if horaire is not None:
            classement.horaire = horaire
        if type_extra is not None:
            classement.type_extra = type_extra
        if participants is not None:
            classement.participants = participants
        if postes is not None:
            classement.postes = postes

        return await self.repo.update(classement)

    async def advance_status(self, classement_id: UUID) -> Optional[Classement]:
        classement = await self.repo.get_by_id(classement_id)
        if not classement:
            return None

        transitions = {
            ClassementStatus.BROUILLON: ClassementStatus.FINALISE,
            ClassementStatus.FINALISE: ClassementStatus.PUBLIE,
        }
        next_status = transitions.get(classement.status)
        if next_status is None:
            raise ValueError("Ce classement est déjà publié.")

        classement.status = next_status
        if next_status == ClassementStatus.PUBLIE:
            classement.published_at = utc_now()

        return await self.repo.update(classement)

    async def delete(self, classement_id: UUID) -> bool:
        classement = await self.repo.get_by_id(classement_id)
        if not classement:
            return False
        if classement.status == ClassementStatus.PUBLIE:
            raise ValueError("Un classement publié ne peut pas être supprimé.")
        return await self.repo.delete(classement_id)
