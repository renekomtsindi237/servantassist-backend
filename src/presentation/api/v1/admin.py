"""
Admin-only endpoints for managing invitations and restricted roles
"""
import secrets
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.invitation import InvitationCode
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.invitation_repository import InvitationCodeRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_admin_user
from src.presentation.schemas.invitation import (
    InvitationCodeCreate,
    InvitationCodeResponse,
    InvitationCodeListResponse
)
from src.presentation.schemas.auth import UserCreate, UserResponse
from src.application.services.auth_service import AuthService

router = APIRouter(tags=["admin"])


def generate_invitation_code() -> str:
    """Generate a unique invitation code format: INV-{random}"""
    random_part = secrets.token_hex(6).upper()  # 12 char hex
    return f"INV-{random_part}"


@router.post("/invitations", response_model=InvitationCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    request: InvitationCodeCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create invitation code for PARENT or AUMÔNIER role
    
    Admin only. Generates a unique code that users can use to register with restricted roles.
    If phone_number is provided and WhatsApp is configured, the code will be sent automatically.
    """
    from src.infrastructure.services.whatsapp_service import WhatsAppService
    
    # Validate role
    if request.role not in ["PARENT", "AUMÔNIER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be PARENT or AUMÔNIER"
        )
    
    # Generate unique code
    code = generate_invitation_code()
    
    # Create invitation (no auto-expiration, admin controls lifespan)
    invitation = InvitationCode(
        code=code,
        role=request.role,
        email=request.email,
        phone_number=request.phone_number,
        created_by=current_admin.id,
        notes=request.notes
    )
    
    invitation_repo = InvitationCodeRepository(session)
    created = await invitation_repo.create(invitation)
    
    # Send WhatsApp message if phone number provided
    if request.phone_number:
        whatsapp_service = WhatsAppService()
        sent = await whatsapp_service.send_invitation_code(
            phone_number=request.phone_number,
            code=code,
            parent_name=request.email.split('@')[0]  # Use email prefix as name
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
            detail="Invitation not found"
        )
    
    # Only admin who created it can revoke
    if invitation.created_by != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke invitations you created"
        )
    
    await invitation_repo.revoke(invitation_id)


@router.post("/users/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create an ADMIN user
    
    Admin only. Direct creation (no invitation code needed).
    IMPORTANT: Only ONE admin can exist at a time (UNIQUE).
    """
    # Override role to ensure it's ADMIN
    user_data.role = UserRole.ADMIN
    
    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo, None)
    
    created_user = await auth_service.register_user(
        user_data,
        invitation_code=None,
        admin_id=current_admin.id  # Track that admin created this
    )
    
    return created_user


@router.post("/users/aumônier", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_aumonier(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create an AUMÔNIER user
    
    Admin only. Direct creation (no invitation code needed).
    IMPORTANT: Only ONE aumônier can exist at a time.
    """
    # Override role to ensure it's AUMÔNIER
    user_data.role = UserRole.AUMÔNIER
    
    # Check if aumônier already exists
    user_repo = UserRepository(session)
    from sqlalchemy import select
    stmt = select(User).where(User.role == UserRole.AUMÔNIER)
    result = await session.exec(stmt)
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An AUMÔNIER already exists. There can only be one."
        )
    
    auth_service = AuthService(user_repo, None)
    created_user = await auth_service.register_user(
        user_data,
        invitation_code=None,
        admin_id=current_admin.id  # Track that admin created this
    )
    
    return created_user


@router.post("/users/parent", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_parent_direct(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Create a PARENT user directly (without invitation code)
    
    Admin only. Alternative to invitation-based flow for direct creation.
    """
    # Override role to ensure it's PARENT
    user_data.role = UserRole.PARENT
    
    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo, None)
    
    created_user = await auth_service.register_user(
        user_data,
        invitation_code=None,
        admin_id=current_admin.id
    )
    
    return created_user
