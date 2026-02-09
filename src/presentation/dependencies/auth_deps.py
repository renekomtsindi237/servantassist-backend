from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from src.core.entities.user import User, UserRole
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.auth import TokenData

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Decode JWT, extract email + role, and fetch user from DB."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except (JWTError, ValidationError):
        raise credentials_exception

    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception

    # Vérification de cohérence : le rôle du JWT doit correspondre au rôle en BDD
    if user.role != token_data.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role mismatch. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


async def get_current_aumonier_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require AUMÔNIER role."""
    if current_user.role != UserRole.AUMÔNIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AUMÔNIER can access this resource",
        )
    return current_user


async def get_current_admin_or_aumonier(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require ADMIN or AUMÔNIER role (for event management)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.AUMÔNIER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls l'administrateur et l'aumonier peuvent effectuer cette action.",
        )
    return current_user


async def get_current_parent_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require PARENT role."""
    if current_user.role != UserRole.PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PARENT can access this resource",
        )
    return current_user


async def get_current_servant_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require SERVANT role."""
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SERVANT can access this resource",
        )
    return current_user


async def get_current_responsable(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Require that the user is a SERVANT with at least one active nomination
    as 'responsable' (leadership position).
    Admin and Aumônier also pass this check.
    """
    if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
        return current_user

    if current_user.role != UserRole.SERVANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les servants responsables peuvent accéder à cette ressource.",
        )

    from src.infrastructure.repositories.responsable_repository import NominationRepository

    nom_repo = NominationRepository(session)
    nominations = await nom_repo.get_active_by_user(current_user.id)
    if not nominations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'occupez aucun poste de responsable.",
        )
    return current_user
