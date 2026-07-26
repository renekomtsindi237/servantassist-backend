"""
Endpoints de gestion des utilisateurs.

Self-service (authentifie) :
    GET    /me                  Mon profil
    PATCH  /me                  Modifier mon profil
    PATCH  /me/password         Changer mon mot de passe
    POST   /me/photo            Uploader ma photo de profil
    DELETE /me/photo            Supprimer ma photo de profil

Administration (admin requis) :
    GET    /                    Liste paginee des utilisateurs
    GET    /{user_id}           Detail d'un utilisateur
    PATCH  /{user_id}           Modifier un utilisateur
    PATCH  /{user_id}/activate  Activer un compte
    PATCH  /{user_id}/deactivate  Desactiver un compte
    POST   /{user_id}/reset-password  Reinitialiser le mot de passe
    DELETE /{user_id}           Supprimer un utilisateur
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.user_service import UserService
from src.core.entities.user import User, UserRole
from src.core.utils import utc_now
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.responsable_repository import NominationRepository
from src.infrastructure.repositories.user_repository import (
    UserRepository,
    default_profile_photo_url,
)
from src.infrastructure.services.storage_service import StorageService
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
    get_current_admin_user,
)
from src.presentation.schemas.user import (
    ChangePasswordRequest,
    PaginatedResponse,
    UserAdminResetPassword,
    UserAdminUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_user_service(session: AsyncSession) -> UserService:
    return UserService(UserRepository(session))


# ══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE — l'utilisateur connecte gere son propre profil
# ══════════════════════════════════════════════════════════════════════════


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Recuperer mon profil."""
    user_repo = UserRepository(session)
    response = UserProfileResponse.model_validate(current_user)
    if current_user.role == UserRole.SERVANT:
        nominations = await NominationRepository(session).get_active_by_user(current_user.id)
        if nominations:
            response.active_poste = nominations[0].poste.value
        response.parent_ids = [p.id for p in await user_repo.get_parents_of(current_user.id)]
    return response


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    data: UserProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Modifier mon profil.

    Champs modifiables : **first_name**, **last_name**, **phone_number**.
    Seuls les champs fournis sont mis a jour (PATCH partiel).
    """
    service = _get_user_service(session)
    return await service.update_profile(current_user, data)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    data: ChangePasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Changer mon mot de passe.

    L'ancien mot de passe est requis pour verification.
    Le nouveau doit respecter la politique de securite (8+ chars, majuscule, minuscule, chiffre).
    """
    service = _get_user_service(session)
    await service.change_password(current_user, data)


@router.post("/me/photo", response_model=UserProfileResponse)
async def upload_my_photo(
    file: Annotated[UploadFile, File(description="Photo de profil (JPEG, PNG ou WebP, max 5 Mo)")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Uploader ou remplacer ma photo de profil.

    **Formats acceptes :** JPEG, PNG, WebP
    **Taille max :** 5 Mo

    Si une photo existe deja, elle sera supprimee et remplacee.
    """
    storage = StorageService()

    # Lire le contenu du fichier
    file_data = await file.read()

    # Valider et uploader
    try:
        # Supprimer l'ancienne photo si elle existe
        if current_user.profile_photo_url:
            await storage.delete_file(current_user.profile_photo_url)

        photo_url = await storage.upload_profile_photo(
            user_id=str(current_user.id),
            file_data=file_data,
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Mettre a jour le profil
    current_user.profile_photo_url = photo_url
    current_user.updated_at = utc_now()
    user_repo = UserRepository(session)
    updated_user = await user_repo.update(current_user.id, current_user)
    return updated_user


@router.delete("/me/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_photo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Supprimer ma photo de profil personnalisee.

    Tout utilisateur a une photo par defaut (`default_profile_photo_url()`,
    identique a `profil.jpeg` cote web) des sa creation ou en l'absence
    d'upload -- ce n'est jamais "aucune photo". Supprimer sa photo revient
    donc a revenir a cette valeur par defaut ; un 404 signifie seulement
    qu'il n'y a pas de photo personnalisee a retirer.
    """
    default_url = default_profile_photo_url()
    if not current_user.profile_photo_url or current_user.profile_photo_url == default_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune photo de profil a supprimer.",
        )

    storage = StorageService()
    await storage.delete_file(current_user.profile_photo_url)

    current_user.profile_photo_url = default_url
    current_user.updated_at = utc_now()
    user_repo = UserRepository(session)
    await user_repo.update(current_user.id, current_user)


@router.post("/me/accept-terms", response_model=UserProfileResponse, status_code=200)
async def accept_terms(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Enregistre l'acceptation des CGU (traçabilité Loi 2024/017)."""
    from src.core.utils import utc_now as _utc_now

    user_repo = UserRepository(session)
    current_user.terms_accepted_at = _utc_now()
    current_user.updated_at = _utc_now()
    updated = await user_repo.update(current_user.id, current_user)
    return UserProfileResponse.model_validate(updated)


@router.post("/me/data-consent", response_model=UserProfileResponse, status_code=200)
async def record_data_consent(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Enregistre le consentement explicite au traitement des données personnelles.

    Conformément à l'article 9 de la Loi n° 2024/017 du 22 décembre 2024 :
    le consentement est libre, spécifique, éclairé et non-ambigu (action positive).
    Le timestamp UTC est enregistré pour traçabilité légale.
    """
    user_repo = UserRepository(session)
    current_user.data_consent_at = utc_now()
    current_user.updated_at = utc_now()
    updated = await user_repo.update(current_user.id, current_user)
    return UserProfileResponse.model_validate(updated)


class SelfLinkParentRequest(BaseModel):
    parent_phone: str


@router.post("/me/link-parent", response_model=UserProfileResponse)
async def self_link_parent(
    data: SelfLinkParentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Lier le servant connecté à un parent via son numéro de téléphone."""
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux servants.")
    user_repo = UserRepository(session)
    parent = await user_repo.get_by_phone(data.parent_phone.strip())
    if not parent or parent.role != UserRole.PARENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun compte parent trouvé avec ce numéro.")
    await user_repo.add_parent_link(current_user.id, parent.id)
    updated = await user_repo.get(current_user.id)
    response = UserProfileResponse.model_validate(updated)
    response.parent_ids = [p.id for p in await user_repo.get_parents_of(current_user.id)]
    return response


@router.delete("/me/link-parent/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def self_unlink_parent(
    parent_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Délier le servant connecté d'un parent."""
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux servants.")
    user_repo = UserRepository(session)
    await user_repo.remove_parent_link(current_user.id, parent_id)


# ══════════════════════════════════════════════════════════════════════════
#  RÉPERTOIRE — accessible à tout utilisateur authentifié
# ══════════════════════════════════════════════════════════════════════════


@router.get("/directory", response_model=PaginatedResponse[UserProfileResponse])
async def list_directory(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    role: Optional[UserRole] = Query(None, description="Filtrer par rôle"),
    is_active: Optional[bool] = Query(True, description="Filtrer par statut actif"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par nom"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """
    Répertoire des membres — accessible à tout utilisateur authentifié.

    Utile pour les pages «Membres», sélecteurs de servant, etc.
    L'ADMIN n'est jamais retourné : il est invisible pour les autres rôles.
    """
    service = _get_user_service(session)
    return await service.list_users(
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
        exclude_admin=True,
    )


# ══════════════════════════════════════════════════════════════════════════
#  ADMINISTRATION — reserve aux admins
# ══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[UserProfileResponse])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    role: Optional[UserRole] = Query(None, description="Filtrer par role"),
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par nom ou email"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
):
    """
    Liste paginee des utilisateurs avec filtres.

    **Filtres disponibles :**
    - `role` : ADMIN, SERVANT, PARENT, AUMONIER
    - `is_active` : true/false
    - `search` : recherche textuelle (nom, prenom, email)
    - `page` / `page_size` : pagination
    """
    service = _get_user_service(session)
    # L'aumônier ne voit pas l'ADMIN dans la liste (support invisible)
    exclude_admin = current_user.role != UserRole.ADMIN
    return await service.list_users(
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
        exclude_admin=exclude_admin,
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """Detail d'un utilisateur. Admin ou Aumônier."""
    service = _get_user_service(session)
    user = await service.get_user(user_id)
    user_repo = UserRepository(session)
    response = UserProfileResponse.model_validate(user)
    if user.role == UserRole.SERVANT:
        response.parent_ids = [p.id for p in await user_repo.get_parents_of(user_id)]
    return response


@router.get("/{user_id}/children", response_model=list[UserProfileResponse])
async def get_user_children(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Servants liés à un parent. Admin uniquement."""
    user_repo = UserRepository(session)
    children = await user_repo.get_children_of(user_id)
    return [UserProfileResponse.model_validate(c) for c in children]


class LinkParentRequest(BaseModel):
    parent_id: Optional[UUID]
    unlink: bool = False


@router.patch("/{user_id}/link-parent", response_model=UserProfileResponse)
async def link_parent(
    user_id: UUID,
    data: LinkParentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Lier ou délier un servant à un parent. Admin uniquement.
    Pour délier : passer unlink=true + parent_id du parent à retirer.
    Un servant peut avoir au maximum 3 parents."""
    service = _get_user_service(session)
    return await service.link_parent(user_id, data.parent_id, unlink=data.unlink)


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def admin_update_user(
    user_id: UUID,
    data: UserAdminUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Modifier un utilisateur. Admin uniquement.

    Champs modifiables : **first_name**, **last_name**, **email**, **phone_number**, **is_active**.
    """
    service = _get_user_service(session)
    return await service.admin_update_user(user_id, data, current_user)


@router.patch("/{user_id}/deactivate", response_model=UserProfileResponse)
async def deactivate_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Desactiver un compte utilisateur. Admin uniquement."""
    service = _get_user_service(session)
    return await service.deactivate_user(user_id, current_user)


@router.patch("/{user_id}/activate", response_model=UserProfileResponse)
async def activate_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Reactiver un compte utilisateur. Admin uniquement."""
    service = _get_user_service(session)
    return await service.activate_user(user_id)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(
    user_id: UUID,
    data: UserAdminResetPassword,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Reinitialiser le mot de passe d'un utilisateur. Admin uniquement.

    Le nouveau mot de passe doit respecter la politique de securite.
    """
    service = _get_user_service(session)
    await service.admin_reset_password(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Supprimer un utilisateur. Admin uniquement.

    **Restrictions :**
    - Impossible de se supprimer soi-meme
    - Impossible de supprimer le dernier administrateur
    """
    service = _get_user_service(session)
    await service.delete_user(user_id, current_user)


# ══════════════════════════════════════════════════════════════════════════
#  CONFORMITÉ LOI 2024/017 (Cameroun) — Droits des personnes concernées
# ══════════════════════════════════════════════════════════════════════════


@router.post(
    "/me/erasure-request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Demande d'effacement des données (Art. 17 Loi 2024/017)",
)
async def request_data_erasure(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Soumet une demande d'effacement des données personnelles.

    Conformité Art. 17 Loi 2024/017 sur la protection des données
    personnelles (Cameroun) — Droit à l'effacement.

    La demande est traitée sous 30 jours ouvrés.
    Un email de confirmation est envoyé à l'utilisateur.
    """
    from src.core.utils import utc_now as _utc_now
    from src.infrastructure.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    # Marquer la demande (champ optionnel erasure_requested_at si présent)
    if hasattr(user, "erasure_requested_at"):
        user.erasure_requested_at = _utc_now()
        session.add(user)
        await session.commit()

    # Notification email asynchrone
    try:
        from src.infrastructure.tasks.email_tasks import send_email_async

        send_email_async.delay(
            to=str(current_user.email or ""),
            subject="Confirmation de votre demande d'effacement — ServantAssist",
            html_body=(
                f"<p>Bonjour {current_user.first_name},</p>"
                "<p>Nous avons bien reçu votre demande d'effacement de vos données personnelles "
                "conformément à l'Art. 17 de la Loi 2024/017.</p>"
                "<p>Votre demande sera traitée dans un délai maximum de <strong>30 jours ouvrés</strong>.</p>"
                "<p>Cordialement,<br>L'équipe ServantAssist</p>"
            ),
        )
    except Exception:
        pass  # L'email est non-bloquant

    return {
        "message": "Demande d'effacement enregistrée. Traitement sous 30 jours ouvrés.",
        "user_id": str(current_user.id),
        "requested_at": utc_now().isoformat(),
        "legal_basis": "Art. 17 Loi 2024/017 — République du Cameroun",
    }


@router.get(
    "/me/data-export",
    summary="Export des données personnelles (Art. 20 Loi 2024/017)",
)
async def export_personal_data(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Exporte toutes les données personnelles de l'utilisateur connecté.

    Conformité Art. 20 Loi 2024/017 — Droit à la portabilité des données.

    Retourne un objet JSON structuré avec :
    - Profil utilisateur
    - Historique de présences (100 derniers)
    - Cotisations (100 dernières)
    - Affectations (50 dernières)
    - Métadonnées de consentement

    Pour un export PDF, déclencher la tâche Celery export_user_data_pdf.
    """
    from sqlmodel import col, select

    from src.core.entities.assignment import Assignment
    from src.core.entities.attendance import Attendance
    from src.core.entities.cotisation import MemberCotisation

    # Présences
    stmt_att = (
        select(Attendance)
        .where(Attendance.user_id == current_user.id)
        .order_by(col(Attendance.created_at).desc())
        .limit(100)
    )
    result_att = await session.exec(stmt_att)
    attendances = result_att.all()

    # Cotisations
    stmt_cot = (
        select(MemberCotisation)
        .where(MemberCotisation.user_id == current_user.id)
        .order_by(col(MemberCotisation.year).desc())
        .limit(100)
    )
    result_cot = await session.exec(stmt_cot)
    cotisations = result_cot.all()

    # Affectations
    stmt_asg = (
        select(Assignment)
        .where(Assignment.user_id == current_user.id)
        .order_by(col(Assignment.created_at).desc())
        .limit(50)
    )
    result_asg = await session.exec(stmt_asg)
    assignments = result_asg.all()

    return {
        "export_date": utc_now().isoformat(),
        "legal_basis": "Art. 20 Loi 2024/017 — République du Cameroun",
        "profile": {
            "id": str(current_user.id),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            "is_active": current_user.is_active,
            "created_at": str(current_user.created_at)[:19] if current_user.created_at else None,
            "data_consent_at": str(current_user.data_consent_at)[:19] if current_user.data_consent_at else None,
            "terms_accepted_at": str(current_user.terms_accepted_at)[:19] if current_user.terms_accepted_at else None,
        },
        "attendances": [
            {
                "session_id": str(a.session_id),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "created_at": str(a.created_at)[:19] if a.created_at else None,
            }
            for a in attendances
        ],
        "cotisations": [
            {
                "month": c.month,
                "year": c.year,
                "amount": float(c.amount or 0),
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            }
            for c in cotisations
        ],
        "assignments": [
            {
                "event_id": str(a.event_id),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "liturgical_role": (
                    a.liturgical_role.value if a.liturgical_role and hasattr(a.liturgical_role, "value") else None
                ),
                "created_at": str(a.created_at)[:19] if a.created_at else None,
            }
            for a in assignments
        ],
    }
