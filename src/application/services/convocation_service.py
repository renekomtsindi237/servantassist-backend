"""
Service metier pour le module Convocation (Art. 48-49 du reglement interieur).

Formalise la convocation des parents : jusqu'ici le systeme se contentait de
calculer un indicateur (`needs_parent_convocation`) sans jamais enregistrer
de convocation structuree ni suivre de delai de reponse.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.convocation import Convocation, ConvocationMotif, ConvocationStatus
from src.core.entities.user import UserRole
from src.core.interfaces.repositories import IConvocationRepository, IUserRepository
from src.core.utils import utc_now
from src.presentation.schemas.convocation import ConvocationCreate, ConvocationResponse


class ConvocationService:
    """Logique metier des convocations de parents."""

    def __init__(
        self,
        convocation_repo: IConvocationRepository,
        user_repo: IUserRepository,
    ):
        self.convocation_repo = convocation_repo
        self.user_repo = user_repo

    async def create_convocation(self, data: ConvocationCreate, convened_by: UUID) -> ConvocationResponse:
        """Convoquer manuellement les parents d'un servant."""
        servant = await self.user_repo.get(data.servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )
        if servant.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les servants peuvent faire l'objet d'une convocation de leurs parents.",
            )

        convocation = Convocation(
            servant_id=data.servant_id,
            motif=data.motif,
            details=data.details,
            convened_by=convened_by,
        )
        created = await self.convocation_repo.create(convocation)
        return ConvocationResponse.model_validate(created)

    async def create_if_not_pending(
        self,
        servant_id: UUID,
        motif: ConvocationMotif,
        details: Optional[str],
        convened_by: UUID,
    ) -> Optional[Convocation]:
        """
        Cree une convocation pour ce motif, sauf si une convocation EN_ATTENTE
        du meme motif existe deja pour ce servant (idempotence — evite les
        doublons si le declencheur automatique se repete).
        """
        existing = await self.convocation_repo.get_pending_by_servant_and_motif(servant_id, motif)
        if existing:
            return None
        convocation = Convocation(
            servant_id=servant_id,
            motif=motif,
            details=details,
            convened_by=convened_by,
        )
        return await self.convocation_repo.create(convocation)

    async def mark_honored(
        self, convocation_id: UUID, honored_by: UUID, notes: Optional[str] = None
    ) -> ConvocationResponse:
        """Marque une convocation comme honoree (presentation d'un parent, Art. 49)."""
        convocation = await self.convocation_repo.get(convocation_id)
        if not convocation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocation introuvable.",
            )
        if convocation.status != ConvocationStatus.EN_ATTENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cette convocation n'est plus en attente (statut = {convocation.status.value}).",
            )

        convocation.status = ConvocationStatus.HONOREE
        convocation.honored_at = utc_now()
        convocation.honored_by = honored_by
        if notes:
            convocation.notes = notes

        updated = await self.convocation_repo.update(convocation)
        return ConvocationResponse.model_validate(updated)

    async def get_convocation(self, convocation_id: UUID) -> ConvocationResponse:
        convocation = await self.convocation_repo.get(convocation_id)
        if not convocation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocation introuvable.",
            )
        return ConvocationResponse.model_validate(convocation)

    async def list_for_servant(self, servant_id: UUID) -> List[ConvocationResponse]:
        convocations = await self.convocation_repo.list_by_servant(servant_id)
        return [ConvocationResponse.model_validate(c) for c in convocations]

    async def process_expired_convocations(self) -> dict:
        """
        Traite les convocations EN_ATTENTE dont le delai de reponse (Art. 49)
        est depasse : passage a SANS_REPONSE + suspension du servant.
        """
        expired = await self.convocation_repo.list_pending_past_deadline()
        processed = 0
        for convocation in expired:
            convocation.status = ConvocationStatus.SANS_REPONSE
            await self.convocation_repo.update(convocation)

            servant = await self.user_repo.get(convocation.servant_id)
            if servant and servant.is_active:
                servant.is_active = False
                servant.updated_at = utc_now()
                await self.user_repo.update(servant.id, servant)
            processed += 1

        return {"expired_convocations_processed": processed}
