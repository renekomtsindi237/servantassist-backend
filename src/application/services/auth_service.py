from datetime import timedelta
from typing import Optional, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select

from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.invitation_repository import InvitationCodeRepository
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.schemas.auth import UserCreate, UserLogin, UserPhoneLogin, Token


class AuthService:
    def __init__(self, user_repository: UserRepository, invitation_repository: Optional[InvitationCodeRepository] = None):
        self.user_repository = user_repository
        self.invitation_repository = invitation_repository

    async def authenticate_user(self, login_data: Union[UserLogin, UserPhoneLogin]) -> User:
        """
        Authenticate user based on role:
        - ADMIN/AUMÔNIER: Email login ONLY (via UserLogin)
        - PARENT/SERVANT: Phone login ONLY (via UserPhoneLogin)
        
        Raises 403 if a user tries the wrong login method for their role.
        """
        if isinstance(login_data, UserLogin):
            # Email-based login — réservé ADMIN/AUMÔNIER
            user = await self.user_repository.get_by_email(login_data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Vérifier que ce user a le droit de se connecter par email
            if user.role not in (UserRole.ADMIN, UserRole.AUMÔNIER):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Les utilisateurs {user.role.value} doivent se connecter avec leur numéro de téléphone",
                )
        else:
            # Phone-based login — réservé PARENT/SERVANT
            user = await self.user_repository.get_by_phone(login_data.phone_number)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect phone number or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Vérifier que ce user a le droit de se connecter par téléphone
            if user.role not in (UserRole.PARENT, UserRole.SERVANT):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Les utilisateurs {user.role.value} doivent se connecter avec leur email",
                )

        # Verify password
        if not SecurityUtils.verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        return user

    async def register_user(self, user_create: UserCreate, invitation_code: Optional[str] = None, admin_id: Optional[UUID] = None) -> User:
        """
        Register a new user with role-based validation

        Rules:
        - SERVANT: Self-registration allowed (no invitation needed)
        - PARENT: Requires valid invitation code
        - AUMÔNIER: Only admin can create (not self-register)
        - ADMIN: Only admin can create
        """
        existing_user = await self.user_repository.get_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check phone uniqueness for PARENT/SERVANT
        if user_create.role in [UserRole.PARENT, UserRole.SERVANT] and user_create.phone_number:
            existing_by_phone = await self.user_repository.get_by_phone(user_create.phone_number)
            if existing_by_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered",
                )

        # Role-based registration validation
        if user_create.role == UserRole.SERVANT:
            # ✅ Servants can self-register
            pass

        elif user_create.role == UserRole.PARENT:
            # ❌ Parents MUST use invitation code (sauf si créé par admin)
            if not admin_id:
                if not invitation_code:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Parent registration requires an invitation code",
                    )

                # Validate invitation code
                if not self.invitation_repository:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invitation system not available",
                    )

                invitation = await self.invitation_repository.get_by_code(invitation_code)
                if not invitation:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid invitation code",
                    )

                # If email-specific invitation, verify match
                if invitation.email and invitation.email != user_create.email:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This invitation code is not valid for this email",
                    )

                # If phone-specific invitation, verify match
                if invitation.phone_number and invitation.phone_number != user_create.phone_number:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This invitation code is not valid for this phone number",
                    )

        elif user_create.role == UserRole.ADMIN:
            # ❌ ADMIN can ONLY be created by existing Admin
            # ❌ ADMIN is UNIQUE (only one allowed)
            if not admin_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="ADMIN user can only be created by an administrator",
                )

            # Check if admin already exists
            stmt = select(User).where(User.role == UserRole.ADMIN)
            result = await self.user_repository.session.exec(stmt)
            if result.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An ADMIN already exists. There can only be one.",
                )

        elif user_create.role == UserRole.AUMÔNIER:
            # ❌ AUMÔNIER can ONLY be created by existing Admin
            # ❌ AUMÔNIER is UNIQUE (only one allowed)
            if not admin_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="AUMÔNIER user can only be created by an administrator",
                )

            # Check if aumônier already exists
            stmt = select(User).where(User.role == UserRole.AUMÔNIER)
            result = await self.user_repository.session.exec(stmt)
            if result.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An AUMÔNIER already exists. There can only be one.",
                )

        # Create user
        hashed_password = SecurityUtils.get_password_hash(user_create.password)
        db_user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            role=user_create.role,
            phone_number=user_create.phone_number,
            created_by=admin_id,  # Track who created this user
            invited_by=None,
        )

        created_user = await self.user_repository.create(db_user)

        # Mark invitation as used if applicable
        if user_create.role == UserRole.PARENT and invitation_code and self.invitation_repository:
            await self.invitation_repository.mark_as_used(invitation_code, created_user.id)

        return created_user

    async def create_tokens(self, user: User) -> Token:
        """Create access + refresh tokens with role embedded in the payload."""
        access_token_expires = timedelta(minutes=30)
        access_token = SecurityUtils.create_access_token(
            subject=user.email,
            role=user.role.value,
            expires_delta=access_token_expires,
        )
        refresh_token = SecurityUtils.create_refresh_token(
            subject=user.email,
            role=user.role.value,
        )
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_token(self, refresh_token: str) -> Token:
        from jose import jwt, JWTError
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            if email is None or token_type != "refresh":
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            raise credentials_exception

        return await self.create_tokens(user)

    async def forgot_password(self, email: str, email_service) -> None:
        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            # Return silently to prevent email enumeration
            return

        reset_token = SecurityUtils.create_reset_token(user.email)
        await email_service.send_reset_password_email(
            to_email=user.email,
            token=reset_token,
            user_first_name=user.first_name or "Utilisateur",
        )

    async def reset_password(self, token: str, new_password: str, email_service=None) -> None:
        from jose import jwt, JWTError
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        credentials_exception = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            if email is None or token_type != "reset":
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            raise credentials_exception

        hashed_password = SecurityUtils.get_password_hash(new_password)
        user.hashed_password = hashed_password
        await self.user_repository.update(user.id, user)

        # Envoyer un email de confirmation de changement de mot de passe
        if email_service:
            try:
                await email_service.send_password_changed_email(
                    to_email=user.email,
                    user_first_name=user.first_name or "Utilisateur",
                )
            except Exception:
                # Ne pas bloquer le reset si l'email de confirmation echoue
                pass
