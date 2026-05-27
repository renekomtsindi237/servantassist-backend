"""
Service metier pour le module Sous-groupes.

Regles du reglement interieur :
- Les sous-groupes servent a organiser les tours de service
- Le Delegue et l'Aumonier gerent la repartition
- Un servant appartient a un seul sous-groupe actif
- Le Charge du classement utilise les sous-groupes pour le planning
"""
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.subgroup import SubGroup, SubGroupMember
from src.core.entities.user import User, UserRole
from src.core.interfaces.repositories import ISubGroupRepository
from src.core.interfaces.repositories import ITrainingParticipationRepository
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.subgroup import (
    SubGroupCreate,
    SubGroupMemberAdd,
    SubGroupMemberResponse,
    SubGroupResponse,
    SubGroupUpdate,
)


class SubGroupService:
    """Logique metier des sous-groupes."""

    def __init__(
        self,
        group_repo: ISubGroupRepository,
        user_repo: IUserRepository,
        training_repo: ITrainingParticipationRepository,
    ):
        self.group_repo = group_repo
        self.user_repo = user_repo
        self.training_repo = training_repo

    # ══════════════════════════════════════════════════════════════════
    #  SOUS-GROUPES (CRUD)
    # ══════════════════════════════════════════════════════════════════

    async def create_group(
        self, data: SubGroupCreate, created_by: UUID
    ) -> SubGroupResponse:
        existing = await self.group_repo.get_by_name(data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Un sous-groupe nomme '{data.name}' existe deja.",
            )

        group = SubGroup(
            name=data.name,
            description=data.description,
            service_schedule=data.service_schedule,
            max_members=data.max_members,
            created_by=created_by,
        )
        created = await self.group_repo.create(group)
        return await self._build_group_response(created)

    async def update_group(
        self, group_id: UUID, data: SubGroupUpdate
    ) -> SubGroupResponse:
        group = await self.group_repo.get(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sous-groupe introuvable.",
            )
        if data.name is not None:
            existing = await self.group_repo.get_by_name(data.name)
            if existing and existing.id != group_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Un sous-groupe nomme '{data.name}' existe deja.",
                )
            group.name = data.name
        if data.description is not None:
            group.description = data.description
        if data.service_schedule is not None:
            group.service_schedule = data.service_schedule
        if data.max_members is not None:
            group.max_members = data.max_members
        if data.is_active is not None:
            group.is_active = data.is_active
        group.updated_at = utc_now()

        updated = await self.group_repo.update(group)
        return await self._build_group_response(updated)

    async def get_group(self, group_id: UUID) -> SubGroupResponse:
        group = await self.group_repo.get(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sous-groupe introuvable.",
            )
        return await self._build_group_response(group)

    async def list_groups(self, active_only: bool = True) -> List[SubGroupResponse]:
        groups = await self.group_repo.list_all(active_only=active_only)
        return [await self._build_group_response(g) for g in groups]

    async def delete_group(self, group_id: UUID) -> None:
        group = await self.group_repo.get(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sous-groupe introuvable.",
            )
        await self.group_repo.delete(group_id)

    async def _build_group_response(self, group: SubGroup) -> SubGroupResponse:
        count = await self.group_repo.get_member_count(group.id)
        members_raw = await self.group_repo.get_members(group.id)
        enriched_members = await self.group_repo.enrich_members(members_raw)
        members = [SubGroupMemberResponse(**m) for m in enriched_members]

        return SubGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            service_schedule=group.service_schedule,
            is_active=group.is_active,
            max_members=group.max_members,
            created_by=group.created_by,
            created_at=group.created_at,
            updated_at=group.updated_at,
            member_count=count,
            members=members,
        )

    # ══════════════════════════════════════════════════════════════════
    #  MEMBRES
    # ══════════════════════════════════════════════════════════════════

    async def add_member(
        self, group_id: UUID, data: SubGroupMemberAdd, added_by: UUID
    ) -> SubGroupMemberResponse:
        group = await self.group_repo.get(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sous-groupe introuvable.",
            )
        if not group.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce sous-groupe n'est plus actif.",
            )

        user = await self.user_repo.get(data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )
        if user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les servants peuvent etre dans un sous-groupe.",
            )

        # Verifier si deja dans ce sous-groupe
        existing = await self.group_repo.get_membership(group_id, data.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce servant est deja dans ce sous-groupe.",
            )

        # Verifier s'il est dans un autre sous-groupe
        other = await self.group_repo.get_active_membership(data.user_id)
        if other:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Ce servant est deja dans un autre sous-groupe. "
                    "Retirez-le d'abord de son sous-groupe actuel."
                ),
            )

        # Verifier capacite
        if group.max_members:
            count = await self.group_repo.get_member_count(group_id)
            if count >= group.max_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ce sous-groupe a atteint sa capacite maximale ({group.max_members}).",
                )

        membership = SubGroupMember(
            sub_group_id=group_id,
            user_id=data.user_id,
            added_by=added_by,
        )
        created = await self.group_repo.add_member(membership)
        enriched = await self.group_repo.enrich_member(created)
        return SubGroupMemberResponse(**enriched)

    async def remove_member(
        self, group_id: UUID, user_id: UUID
    ) -> SubGroupMemberResponse:
        membership = await self.group_repo.get_membership(group_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ce servant n'est pas dans ce sous-groupe.",
            )
        updated = await self.group_repo.remove_member(membership)
        enriched = await self.group_repo.enrich_member(updated)
        return SubGroupMemberResponse(**enriched)

    async def get_my_group(self, user_id: UUID) -> Optional[SubGroupResponse]:
        membership = await self.group_repo.get_active_membership(user_id)
        if not membership:
            return None
        group = await self.group_repo.get(membership.sub_group_id)
        if not group:
            return None
        return await self._build_group_response(group)

    async def reclassify_servant(self, user_id: UUID) -> Optional[SubGroupResponse]:
        """
        Reclassification automatique selon l'Article 26 :
        - Aspirants : < 12 ans
        - Confirmés : >= 12 ans
        - Aînés : >= 15 ans + moyenne >= 14/20
        """
        user = await self.user_repo.get(user_id)
        if not user or user.role != UserRole.SERVANT or not user.birth_date:
            return None

        # Calcul de l'âge
        today = utc_now()
        birth = (
            user.birth_date.replace(tzinfo=timezone.utc)
            if user.birth_date.tzinfo is None
            else user.birth_date
        )
        age = (
            today.year
            - birth.year
            - ((today.month, today.day) < (birth.month, birth.day))
        )

        # Déterminer le groupe cible
        target_name = "ASPIRANTS"
        if age >= 12:
            target_name = "CONFIRMÉS"

        if age >= 15:
            # Vérifier les notes pour les Aînés (Article 26.4)
            stats = await self.training_repo.get_servant_stats(user_id)
            if stats.average_score and stats.average_score >= 70:  # 14/20 = 70%
                target_name = "AÎNÉS"

        # Trouver le groupe
        group = await self.group_repo.get_by_name(target_name)
        if not group:
            # Fallback si le groupe n'existe pas (on ne le crée pas automatiquement
            # pour éviter les erreurs de foreign key sur created_by)
            return None

        # Vérifier si déjà dans ce groupe
        current = await self.group_repo.get_active_membership(user_id)
        if current and current.sub_group_id == group.id:
            return await self._build_group_response(group)

        # Changer de groupe
        if current:
            await self.group_repo.remove_member(current)

        membership = SubGroupMember(
            sub_group_id=group.id,
            user_id=user_id,
            added_by=UUID("00000000-0000-0000-0000-000000000000"),  # System
        )
        # Note: system ID bypass check if repo allows it. In a real app we'd need a valid user.
        # But here we commit to BDD for RI compliance.
        created = await self.group_repo.add_member(membership)
        return await self._build_group_response(group)
