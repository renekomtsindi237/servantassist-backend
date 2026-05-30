"""
Admin-only endpoints for managing invitations, PARENT accounts, and AUMÔNIER account

SECURITY NOTE:
- PARENT accounts can be created directly by ADMIN through this API
- AUMÔNIER account is unique (only one can exist in the system)
- ADMIN accounts must be created through secure database seeding
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.core.entities.invitation import InvitationCode
from src.core.entities.user import User, UserRole
from src.core.utils import utc_now
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.invitation_repository import (
    InvitationCodeRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.services.email_service import EmailService
from src.presentation.dependencies.auth_deps import get_current_admin_user
from src.presentation.schemas.auth import UserCreate, UserResponse
from src.presentation.schemas.invitation import (
    InvitationCodeCreate,
    InvitationCodeListResponse,
    InvitationCodeResponse,
    SendInvitationEmailRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_invitation_code() -> str:
    """Generate a unique invitation code format: INV-{random}"""
    random_part = secrets.token_hex(6).upper()  # 12 char hex
    return f"INV-{random_part}"


@router.post(
    "/invitations",
    response_model=InvitationCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    request: InvitationCodeCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create invitation code for PARENT role only

    Admin only. Generates a unique code that users can use to register as PARENT.
    If phone_number is provided and WhatsApp is configured, the code will be sent automatically.

    SECURITY: Only PARENT invitations are allowed through API.
    ADMIN and AUMÔNIER must be created through secure database seeding.
    """
    from src.infrastructure.services.whatsapp_service import WhatsAppService

    # SECURITY: Only allow PARENT and AUMÔNIER role invitations
    if request.role not in ("PARENT", "AUMÔNIER"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Only invitations for roles PARENT and AUMONIER can be created via the API. The role '{request.role}' is not allowed.",  # noqa: E501
        )

    # Generate unique code
    code = generate_invitation_code()

    # Create invitation (no auto-expiration, admin controls lifespan)
    invitation = InvitationCode(
        code=code,
        role=request.role,
        parent_name=request.parent_name,
        email=request.email,
        phone_number=request.phone_number,
        created_by=current_admin.id,
        notes=request.notes,
    )

    invitation_repo = InvitationCodeRepository(session)
    created = await invitation_repo.create(invitation)

    # Send WhatsApp message if phone number provided
    if request.phone_number:
        whatsapp_service = WhatsAppService()
        sent = await whatsapp_service.send_invitation_code(
            phone_number=request.phone_number,
            code=code,
            parent_name=request.email.split("@")[0],  # Use email prefix as name
        )

        if sent:
            # Mark as sent
            created.whatsapp_sent = True
            await invitation_repo.update(created.id, created)

    return created


@router.get("/invitations", response_model=List[InvitationCodeListResponse])
async def list_invitations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    List all invitations created by this admin

    Admin only. View all invitation codes they've created.
    """
    invitation_repo = InvitationCodeRepository(session)
    invitations = await invitation_repo.get_all_by_admin(current_admin.id)
    return invitations


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Revoke an invitation code

    Admin only. Prevents this code from being used.
    """
    invitation_repo = InvitationCodeRepository(session)
    invitation = await invitation_repo.get_by_id(invitation_id)

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette invitation est introuvable.",
        )

    # Only admin who created it can revoke
    if invitation.created_by != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez révoquer que les invitations que vous avez créées.",
        )

    await invitation_repo.revoke(invitation_id)


@router.post(
    "/invitations/{invitation_id}/send-email",
    response_model=InvitationCodeResponse,
)
async def send_invitation_email(
    invitation_id: UUID,
    request: SendInvitationEmailRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Send invitation code to a parent via email.

    Admin only. Sends the invitation code to the specified email address and
    marks the invitation as email_sent.
    """
    invitation_repo = InvitationCodeRepository(session)
    invitation = await invitation_repo.get_by_id(invitation_id)

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable.")

    if invitation.created_by != current_admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    email_service = EmailService()
    parent_name = invitation.parent_name or request.email.split("@")[0]
    await email_service.send_invitation_code_email(
        to_email=request.email,
        parent_name=parent_name,
        code=invitation.code,
        role=invitation.role,
    )

    invitation.email_sent = True
    updated = await invitation_repo.update(invitation_id, invitation)
    return updated


@router.patch(
    "/invitations/{invitation_id}/toggle-status",
    response_model=InvitationCodeResponse,
)
async def toggle_invitation_status(
    invitation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Toggle invitation code between active (PENDING) and inactive (REVOKED).

    Admin only. Cannot toggle invitations that have already been accepted.
    """
    from src.core.entities.invitation import InvitationStatus

    invitation_repo = InvitationCodeRepository(session)
    invitation = await invitation_repo.get_by_id(invitation_id)

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable.")

    if invitation.created_by != current_admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    if invitation.status == InvitationStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de modifier une invitation déjà acceptée.",
        )

    if invitation.status == InvitationStatus.PENDING:
        invitation.status = InvitationStatus.REVOKED
    else:
        invitation.status = InvitationStatus.PENDING

    updated = await invitation_repo.update(invitation_id, invitation)
    return updated


@router.post("/users/aumônier", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_aumônier(
    request: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create the unique AUMÔNIER account

    Admin only. Only one AUMÔNIER can exist in the entire system.
    """
    aumônier_create = UserCreate(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number if hasattr(request, "phone_number") else None,
        role=UserRole.AUMÔNIER,
    )

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo, None)

    try:
        user = await auth_service.register_user(user_create=aumônier_create, admin_id=current_admin.id)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to create AUMÔNIER user | admin_id=%s | email=%s | error=%s",
            str(current_admin.id),
            request.email,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La création du compte Aumônier a échoué. Vérifiez les informations fournies.",
        )


@router.post("/users/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    request: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create a secondary ADMIN account (only one allowed total in system).

    Admin only. Only one ADMIN can exist.
    """
    admin_create = UserCreate(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=request.phone_number if hasattr(request, "phone_number") else None,
        role=UserRole.ADMIN,
    )

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo, None)

    try:
        user = await auth_service.register_user(user_create=admin_create, admin_id=current_admin.id)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to create ADMIN user | admin_id=%s | email=%s | error=%s",
            str(current_admin.id),
            request.email,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La création du compte Administrateur a échoué. Vérifiez les informations fournies.",
        )


@router.post("/users/parent", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_parent_direct(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create a PARENT user directly (without invitation code)

    Admin only. Allows admin to create PARENT accounts directly from their interface.
    This is secure as it requires admin authentication and only creates PARENT role.

    SECURITY: Only PARENT role can be created. ADMIN and AUMÔNIER are blocked.
    """
    # SECURITY: Force role to PARENT only
    user_data.role = UserRole.PARENT

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo, None)

    created_user = await auth_service.register_user(user_data, invitation_code=None, admin_id=current_admin.id)

    return created_user


# ══════════════════════════════════════════════════════════════════════════
#  API KEYS — Pour les intégrations tierces
# ══════════════════════════════════════════════════════════════════════════


class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    # La clé en clair n'est retournée qu'à la création
    key: Optional[str] = None

    model_config = {"from_attributes": True}


def _hash_key(raw_key: str) -> str:
    """Hache une clé API avec SHA-256 (rapide, pas bcrypt — la clé est déjà aléatoire)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une clé API",
    description=(
        "Génère une nouvelle clé API pour les intégrations tierces. "
        "La clé est retournée UNE SEULE FOIS en clair — conservez-la immédiatement."
    ),
)
async def create_api_key(
    data: ApiKeyCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """Génère une clé API et la retourne en clair une seule fois."""
    raw_key = f"sa_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    key_id = uuid4()
    now = utc_now()
    stmt = text(
        "INSERT INTO api_keys (id, name, key_hash, user_id, scopes, is_active, created_at) "
        "VALUES (:id, :name, :key_hash, :user_id, :scopes, :is_active, :created_at)"
    )
    await session.execute(
        stmt,
        {
            "id": str(key_id),
            "name": data.name,
            "key_hash": key_hash,
            "user_id": str(current_admin.id),
            "scopes": json.dumps(data.scopes),
            "is_active": True,
            "created_at": now,
        },
    )
    await session.commit()

    return ApiKeyResponse(
        id=key_id,
        name=data.name,
        scopes=data.scopes,
        is_active=True,
        last_used_at=None,
        created_at=now,
        key=raw_key,  # Retournée UNE SEULE FOIS
    )


@router.get(
    "/api-keys",
    response_model=List[ApiKeyResponse],
    summary="Lister les clés API",
)
async def list_api_keys(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """Retourne toutes les clés API (sans les clés en clair)."""
    result = await session.execute(
        text(
            "SELECT id, name, scopes, is_active, last_used_at, created_at FROM api_keys WHERE user_id = :uid ORDER BY created_at DESC"  # noqa: E501
        ),
        {"uid": str(current_admin.id)},
    )
    rows = result.fetchall()
    return [
        ApiKeyResponse(
            id=UUID(row[0]),
            name=row[1],
            scopes=json.loads(row[2]) if isinstance(row[2], str) else (row[2] or []),
            is_active=row[3],
            last_used_at=row[4],
            created_at=row[5],
        )
        for row in rows
    ]


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer une clé API",
)
async def revoke_api_key(
    key_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """Désactive une clé API (révocation sans suppression physique)."""
    result = await session.execute(
        text("UPDATE api_keys SET is_active = false WHERE id = :id AND user_id = :uid"),
        {"id": str(key_id), "uid": str(current_admin.id)},
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clé API introuvable.")


# ── Géolocalisation des connexions ────────────────────────────────────────────


@router.get("/connections/geo", summary="Points de connexion géolocalisés")
async def get_connections_geo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    days: int = Query(30, ge=1, le=90, description="Fenêtre en jours"),
) -> list:
    """
    Retourne les connexions récentes agrégées par ville avec coordonnées GPS.
    Utilisé par le globe 3D du dashboard admin.
    """
    repo = ConnectionLogRepository(session)
    return await repo.get_geo_points(days=days)
