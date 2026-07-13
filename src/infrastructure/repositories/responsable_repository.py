"""
Repository pour les entites Nomination et PosteAction.

Fournit les operations CRUD + enrichissement + filtrage + pagination.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.event import Event
from src.core.entities.responsable import (
    POSTE_MISSIONS,
    POSTE_TO_SLUG,
    ActionCategory,
    ActionStatus,
    Nomination,
    NominationStatus,
    PosteAction,
    PosteResponsable,
)
from src.core.entities.user import User
from src.core.utils import utc_now
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name", "email", "phone_number")


class NominationRepository:
    """Operations sur les nominations aux postes de responsable."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, nomination_id: UUID) -> Optional[Nomination]:
        stmt = select(Nomination).where(Nomination.id == nomination_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_active_by_poste(self, poste: PosteResponsable) -> Optional[Nomination]:
        """Retourne la nomination active pour un poste donne (ou None)."""
        stmt = select(Nomination).where(
            Nomination.poste == poste,
            Nomination.status == NominationStatus.ACTIVE,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_active_by_user(self, user_id: UUID) -> List[Nomination]:
        """Retourne toutes les nominations actives d'un utilisateur."""
        stmt = select(Nomination).where(
            Nomination.user_id == user_id,
            Nomination.status == NominationStatus.ACTIVE,
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def get_active_by_user_and_poste(self, user_id: UUID, poste: PosteResponsable) -> Optional[Nomination]:
        """Verifie si un utilisateur occupe un poste specifique."""
        stmt = select(Nomination).where(
            Nomination.user_id == user_id,
            Nomination.poste == poste,
            Nomination.status == NominationStatus.ACTIVE,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def list_all_active(self) -> List[Nomination]:
        """Toutes les nominations actives."""
        stmt = (
            select(Nomination)
            .where(Nomination.status == NominationStatus.ACTIVE)
            .order_by(Nomination.nominated_at.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def list_history(
        self,
        user_id: Optional[UUID] = None,
        poste: Optional[PosteResponsable] = None,
    ) -> List[Nomination]:
        """Historique des nominations (actives + revoquees)."""
        stmt = select(Nomination).order_by(Nomination.nominated_at.desc())
        if user_id:
            stmt = stmt.where(Nomination.user_id == user_id)
        if poste:
            stmt = stmt.where(Nomination.poste == poste)
        result = await self.session.exec(stmt)
        return result.all()

    # ── Enrichissement ─────────────────────────────────────────────────

    async def enrich_nomination(self, nomination: Nomination) -> Dict:
        """Enrichit une nomination avec les infos utilisateur et poste."""
        user_stmt = select(User).where(User.id == nomination.user_id)
        user_result = await self.session.exec(user_stmt)
        user = user_result.first()
        if user:
            decrypt_str_fields(user, _USER_PII)

        missions = POSTE_MISSIONS.get(nomination.poste, {})
        slug = POSTE_TO_SLUG.get(nomination.poste, "")

        return {
            "id": nomination.id,
            "user_id": nomination.user_id,
            "poste": nomination.poste,
            "poste_titre": missions.get("titre", nomination.poste.value),
            "poste_slug": slug,
            "status": nomination.status,
            "nominated_by": nomination.nominated_by,
            "notes": nomination.notes,
            "nominated_at": nomination.nominated_at,
            "revoked_at": nomination.revoked_at,
            "revoked_by": nomination.revoked_by,
            "user_first_name": user.first_name if user else None,
            "user_last_name": user.last_name if user else None,
            "user_email": user.email if user else None,
            "user_phone": user.phone_number if user else None,
        }

    async def enrich_nominations(self, nominations: List[Nomination]) -> List[Dict]:
        return [await self.enrich_nomination(n) for n in nominations]

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(self, nomination: Nomination) -> Nomination:
        self.session.add(nomination)
        await self.session.commit()
        await self.session.refresh(nomination)
        return nomination

    async def update(self, nomination: Nomination) -> Nomination:
        self.session.add(nomination)
        await self.session.commit()
        await self.session.refresh(nomination)
        return nomination


class PosteActionRepository:
    """Operations sur les actions des responsables."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, action_id: UUID) -> Optional[PosteAction]:
        stmt = select(PosteAction).where(PosteAction.id == action_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_id(self, action_id: UUID) -> Optional[PosteAction]:
        """Alias pour get() pour compatibility."""
        return await self.get(action_id)

    async def list_by_poste(
        self,
        poste: PosteResponsable,
        *,
        category: Optional[ActionCategory] = None,
        status: Optional[ActionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[PosteAction], int]:
        """Liste paginee des actions d'un poste."""
        stmt = select(PosteAction).where(PosteAction.poste == poste)

        if category:
            stmt = stmt.where(PosteAction.category == category)
        if status:
            stmt = stmt.where(PosteAction.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(PosteAction.created_at.desc())

        result = await self.session.exec(stmt)
        return result.all(), total

    async def list_with_filters(
        self,
        *,
        poste: Optional[PosteResponsable] = None,
        category: Optional[ActionCategory] = None,
        status: Optional[ActionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """Liste toutes les actions avec filtres optionnels et pagination."""
        stmt = select(PosteAction)

        if poste:
            stmt = stmt.where(PosteAction.poste == poste)
        if category:
            stmt = stmt.where(PosteAction.category == category)
        if status:
            stmt = stmt.where(PosteAction.status == status)

        # Compter le total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Paginer et trier
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(PosteAction.created_at.desc())

        result = await self.session.exec(stmt)
        items = result.all()

        total_pages = (total + page_size - 1) // page_size
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def list_by_visibility(
        self,
        user_id: UUID,
        *,
        poste: Optional[PosteResponsable] = None,
        category: Optional[ActionCategory] = None,
        status: Optional[ActionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """Liste les actions visibles pour un utilisateur (ses actions + actions publiées)."""
        stmt = select(PosteAction).where(
            or_(
                PosteAction.created_by == user_id,
                PosteAction.status == ActionStatus.PUBLIE,
            )
        )

        if poste:
            stmt = stmt.where(PosteAction.poste == poste)
        if category:
            stmt = stmt.where(PosteAction.category == category)
        if status:
            stmt = stmt.where(PosteAction.status == status)

        # Compter le total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Paginer et trier
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(PosteAction.created_at.desc())

        result = await self.session.exec(stmt)
        items = result.all()

        total_pages = (total + page_size - 1) // page_size
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def list_by_user(self, user_id: UUID) -> List[PosteAction]:
        """Toutes les actions creees par un utilisateur."""
        stmt = select(PosteAction).where(PosteAction.created_by == user_id).order_by(PosteAction.created_at.desc())
        result = await self.session.exec(stmt)
        return result.all()

    async def count_by_poste_and_status(self, poste: PosteResponsable) -> Dict[str, int]:
        """Compte les actions par statut pour un poste donne."""
        counts = {}
        for s in ActionStatus:
            stmt = select(func.count()).where(
                PosteAction.poste == poste,
                PosteAction.status == s,
            )
            result = await self.session.exec(stmt)
            counts[s.value] = result.one()
        return counts

    async def get_recent_by_poste(self, poste: PosteResponsable, limit: int = 5) -> List[PosteAction]:
        """Les N actions les plus recentes d'un poste."""
        stmt = (
            select(PosteAction).where(PosteAction.poste == poste).order_by(PosteAction.created_at.desc()).limit(limit)
        )
        result = await self.session.exec(stmt)
        return result.all()

    # ── Enrichissement ─────────────────────────────────────────────────

    async def enrich_action(self, action: PosteAction) -> Dict:
        """Enrichit une action avec les infos auteur et cibles."""
        # Auteur
        author_stmt = select(User).where(User.id == action.created_by)
        author_result = await self.session.exec(author_stmt)
        author = author_result.first()
        if author:
            decrypt_str_fields(author, _USER_PII)

        # Cible utilisateur (optionnel)
        target_user_name = None
        if action.target_user_id:
            t_stmt = select(User).where(User.id == action.target_user_id)
            t_result = await self.session.exec(t_stmt)
            target_user = t_result.first()
            if target_user:
                decrypt_str_fields(target_user, _USER_PII)
                target_user_name = f"{target_user.first_name} {target_user.last_name}"

        # Cible evenement (optionnel)
        target_event_title = None
        if action.target_event_id:
            e_stmt = select(Event).where(Event.id == action.target_event_id)
            e_result = await self.session.exec(e_stmt)
            target_event = e_result.first()
            if target_event:
                target_event_title = target_event.title

        return {
            "id": action.id,
            "poste": action.poste,
            "category": action.category,
            "title": action.title,
            "content": action.content,
            "target_user_id": action.target_user_id,
            "target_event_id": action.target_event_id,
            "amount": action.amount,
            "action_date": action.action_date,
            "status": action.status,
            "extra_data": action.extra_data,
            "created_by": action.created_by,
            "created_at": action.created_at,
            "updated_at": action.updated_at,
            "author_first_name": author.first_name if author else None,
            "author_last_name": author.last_name if author else None,
            "target_user_name": target_user_name,
            "target_event_title": target_event_title,
        }

    async def enrich_actions(self, actions: List[PosteAction]) -> List[Dict]:
        return [await self.enrich_action(a) for a in actions]

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(
        self,
        poste: PosteResponsable,
        category: ActionCategory,
        title: str,
        content: Optional[str] = None,
        target_user_id: Optional[UUID] = None,
        target_event_id: Optional[UUID] = None,
        amount: Optional[float] = None,
        action_date: Optional[datetime] = None,
        status: Optional[ActionStatus] = None,
        extra_data: Optional[str] = None,
        created_by: Optional[UUID] = None,
    ) -> PosteAction:
        """Crée une nouvelle action."""
        action = PosteAction(
            poste=poste,
            category=category,
            title=title,
            content=content,
            target_user_id=target_user_id,
            target_event_id=target_event_id,
            amount=amount,
            action_date=action_date,
            extra_data=extra_data,
            created_by=created_by,
            status=status or ActionStatus.BROUILLON,
        )
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def update(self, action_id: UUID, data: Dict) -> Optional[PosteAction]:
        """Modifie une action existante par son ID avec un dictionnaire de données."""
        action = await self.get(action_id)
        if not action:
            return None

        for key, value in data.items():
            if hasattr(action, key) and value is not None:
                setattr(action, key, value)

        action.updated_at = utc_now()
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def delete(self, action_id: UUID) -> bool:
        stmt = select(PosteAction).where(PosteAction.id == action_id)
        result = await self.session.exec(stmt)
        entity = result.first()
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False
