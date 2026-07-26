import logging
from datetime import timedelta
from typing import Optional, Union
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select

from src.core.entities.user import User, UserRole
from src.core.events.domain_events import UserInvited, UserRegistered
from src.core.interfaces.repositories import IInvitationRepository, IUserRepository
from src.core.utils import utc_now
from src.infrastructure.events.bus import event_bus
from src.infrastructure.repositories.responsable_repository import NominationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.schemas.auth import Token, UserCreate, UserLogin, UserPhoneLogin

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,  # UserRepository conservé : accès direct à .session nécessaire
        invitation_repository: Optional[IInvitationRepository] = None,
    ):
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

    async def authenticate_oauth(self, provider: str, id_token: str) -> User:
        """
        Connexion via jeton d'identité Google, déjà vérifié par
        `oauth_verifier`. **Ne crée jamais de compte** — l'inscription reste
        le formulaire multi-étapes existant ; l'utilisateur doit déjà exister
        (retrouvé par email vérifié) pour que la connexion OAuth aboutisse.
        """
        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.services.oauth_verifier import (
            OAuthVerificationError,
            verify_google_id_token,
        )

        settings = get_settings()
        try:
            identity = verify_google_id_token(id_token, settings.GOOGLE_OAUTH_CLIENT_ID)
        except OAuthVerificationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if not identity.email or not identity.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="L'e-mail associé à ce compte n'est pas vérifié par le fournisseur.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.user_repository.get_by_email(identity.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun compte ServantAssist n'est associé à cet e-mail. Veuillez d'abord vous inscrire.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if user.oauth_provider != provider or user.oauth_subject != identity.subject:
            user.oauth_provider = provider
            user.oauth_subject = identity.subject
            try:
                user = await self.user_repository.update(user.id, user)
            except Exception:  # noqa: BLE001
                logger.warning("Échec de la liaison OAuth pour %s (non bloquant)", user.id)

        return user

    async def register_user(
        self,
        user_create: UserCreate,
        invitation_code: Optional[str] = None,
        admin_id: Optional[UUID] = None,
        skip_age_check: bool = False,
        require_phone_verification: bool = False,
        phone_verification_repository=None,
    ) -> User:
        """
        Register a new user with role-based validation

        Rules:
        - SERVANT ≥ 13 ans: Self-registration with phone (email reste NULL si non fourni)
        - SERVANT < 13 ans: Created by parent via POST /parent/children (skip_age_check=True)
        - PARENT: Requires valid invitation code
        - AUMÔNIER: Only admin can create (not self-register)
        - ADMIN: Only admin can create

        `require_phone_verification=True` (utilisé uniquement par l'inscription
        publique SERVANT/PARENT via POST /auth/register) exige un
        `phone_verification_token` valide obtenu via /auth/register/verify-phone-code.
        Non utilisé par POST /parent/children (skip_age_check=True), qui crée des
        enfants sans téléphone vérifiable.
        """
        # Aucune génération d'email technique : NULL reste NULL. L'identité du
        # JWT repose sur User.id (voir create_tokens), pas sur l'email.
        if user_create.email:
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

        # Validation âge < 13 ans : doit être créé par le parent
        if not skip_age_check and getattr(user_create, "birth_date", None):
            birth = user_create.birth_date
            if hasattr(birth, "date"):
                birth = birth.date()
            from datetime import date as _date

            age = (_date.today() - birth).days // 365
            if age < 13 and not getattr(user_create, "parent_id", None):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Les servants de moins de 13 ans doivent être inscrits"
                        " par leur parent depuis son tableau de bord."
                    ),
                )

        # Role-based registration validation
        if user_create.role == UserRole.SERVANT:
            # ✅ Servants can self-register
            ...

        elif user_create.role == UserRole.PARENT:
            # ❌ Parents MUST use invitation code (sauf si créé par admin)
            if not admin_id:
                if not invitation_code:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="L'inscription en tant que Parent nécessite un code d'invitation.",
                    )

                # Validate invitation code
                if not self.invitation_repository:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Le système d'invitation est temporairement indisponible.",
                    )

                invitation = await self.invitation_repository.get_by_code(invitation_code)
                if not invitation:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invitation code is invalid or already used.",
                    )

                # If email-specific invitation, verify match
                if invitation.email and invitation.email != user_create.email:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This invitation code is not valid for this email address.",
                    )

                # If phone-specific invitation, verify match
                if invitation.phone_number and invitation.phone_number != user_create.phone_number:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This invitation code is not valid for this phone number.",
                    )

        elif user_create.role == UserRole.ADMIN:
            # ❌ ADMIN can ONLY be created by existing Admin
            # ❌ ADMIN is UNIQUE (only one allowed)
            if not admin_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Administrator account can only be created by an existing administrator.",
                )

            # Check if admin already exists
            stmt = select(User).where(User.role == UserRole.ADMIN)
            result = await self.user_repository.session.exec(stmt)
            if result.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An Administrator account already exists. There can only be one.",
                )

        elif user_create.role == UserRole.AUMÔNIER:
            # ❌ AUMÔNIER can ONLY be created by existing Admin
            # ❌ AUMÔNIER is UNIQUE (only one allowed)
            if not admin_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Aumonier account can only be created by an administrator.",
                )

            # Check if aumônier already exists
            stmt = select(User).where(User.role == UserRole.AUMÔNIER)
            result = await self.user_repository.session.exec(stmt)
            if result.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An Aumonier account already exists. There can only be one.",
                )

        # Vérification du numéro de téléphone (inscription publique uniquement) —
        # dernière porte avant la création effective du compte, pour laisser les
        # autres règles métier (email/téléphone dupliqué, âge, invitation) s'exprimer
        # avec leur propre code d'erreur en premier.
        if require_phone_verification:
            from src.infrastructure.security.field_encryption import get_encryptor

            token = getattr(user_create, "phone_verification_token", None)
            verified_entry = None
            if token and user_create.phone_number and phone_verification_repository is not None:
                phone_hmac = get_encryptor().hmac_index(user_create.phone_number)
                verified_entry = await phone_verification_repository.get_by_token(phone_hmac, token)
            if not verified_entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Numéro de téléphone non vérifié. Veuillez vérifier votre numéro avant de continuer.",
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
            birth_date=getattr(user_create, "birth_date", None),
            created_by=admin_id,  # Track who created this user
            invited_by=None,
        )

        created_user = await self.user_repository.create(db_user)

        # Lier au parent via junction table si parent_id fourni
        _parent_id = getattr(user_create, "parent_id", None)
        if _parent_id:
            await self.user_repository.add_parent_link(created_user.id, _parent_id)

        # Mark invitation as used if applicable
        if user_create.role == UserRole.PARENT and invitation_code and self.invitation_repository:
            await self.invitation_repository.mark_as_used(invitation_code, created_user.id)

        await event_bus.publish(
            UserRegistered(
                user_id=created_user.id,
                email=user_create.email,
                first_name=user_create.first_name,
                role=user_create.role.value,
                created_by_admin=admin_id is not None,
            )
        )
        return created_user

    async def create_tokens(self, user: User) -> Token:
        """Create access + refresh tokens with role and position embedded in the payload.

        Le `sub` du JWT est `user.id` (toujours présent), pas l'email — l'email
        est optionnel pour SERVANT/PARENT (identifiant de connexion = téléphone).

        The `position` claim is sourced from the servant's active `Nomination`
        (Nomination/PosteResponsable is the sole source of truth for postes).
        """
        access_token_expires = timedelta(minutes=30)
        position: Optional[str] = None
        if user.role == UserRole.SERVANT:
            nominations = await NominationRepository(self.user_repository.session).get_active_by_user(user.id)
            if nominations:
                position = nominations[0].poste.value
        access_token = SecurityUtils.create_access_token(
            subject=user.id,
            role=user.role.value,
            position=position,
            expires_delta=access_token_expires,
        )
        refresh_token = SecurityUtils.create_refresh_token(
            subject=user.id,
            role=user.role.value,
            position=position,
        )
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_token(self, refresh_token: str) -> Token:
        import time as _time

        import jwt

        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.security.token_blacklist import token_blacklist

        settings = get_settings()

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            sub: str = payload.get("sub")
            token_type: str = payload.get("type")
            old_jti: str = payload.get("jti")
            exp: float = payload.get("exp", _time.time())
            if sub is None or token_type != "refresh":
                raise credentials_exception
            user_id = UUID(sub)
        except (jwt.PyJWTError, ValueError):
            raise credentials_exception

        # Vérifier que le refresh token n'a pas été révoqué
        if old_jti and await token_blacklist.is_revoked(old_jti):
            raise credentials_exception

        user = await self.user_repository.get(user_id)
        if not user or not user.is_active:
            raise credentials_exception

        # Révoquer l'ancien refresh token (rotation)
        if old_jti:
            await token_blacklist.revoke(old_jti, exp)

        return await self.create_tokens(user)

    async def request_reset_code(
        self,
        email: str,
        code_repository,
        email_service,
    ) -> None:
        """Génère un code OTP 6 chiffres et l'envoie par email (flow mobile)."""
        import random
        from datetime import timedelta

        from src.core.entities.password_reset_code import PasswordResetCode

        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            return  # Silencieux pour prévenir l'énumération

        # Nettoyer les anciens codes pour cet utilisateur
        await code_repository.delete_for_user(user.id)
        await code_repository.delete_expired()

        code = f"{random.randint(0, 999999):06d}"
        expires_at = utc_now() + timedelta(minutes=15)

        entry = PasswordResetCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
        )
        await code_repository.create(entry)

        try:
            await email_service.send_reset_code_email(
                to_email=email,
                code=code,
                user_first_name=user.first_name or "Utilisateur",
            )
        except Exception as exc:
            logger.warning("Envoi code OTP échoué | email=%s | error=%s", email, str(exc))

    async def verify_reset_code(
        self,
        email: str,
        code: str,
        code_repository,
    ) -> str:
        """Vérifie le code OTP et retourne un JWT reset_token."""
        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Compte introuvable ou inactif.",
            )

        entry = await code_repository.get_valid(user.id, code)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code invalide ou expiré.",
            )

        await code_repository.mark_used(entry.id)

        return SecurityUtils.create_reset_token(user.id)

    async def request_reset_code_phone(self, phone_number: str, code_repository) -> None:
        """Génère un code OTP pour réinitialisation via numéro de téléphone (SERVANT/PARENT)."""
        import random
        from datetime import timedelta

        from src.core.entities.password_reset_code import PasswordResetCode
        from src.infrastructure.services.whatsapp_service import WhatsAppService

        user = await self.user_repository.get_by_phone(phone_number)
        if not user or not user.is_active:
            return  # Silencieux pour prévenir l'énumération

        await code_repository.delete_for_user(user.id)
        await code_repository.delete_expired()

        code = f"{random.randint(0, 999999):06d}"
        expires_at = utc_now() + timedelta(minutes=15)
        entry = PasswordResetCode(user_id=user.id, code=code, expires_at=expires_at)
        await code_repository.create(entry)

        try:
            await WhatsAppService().send_otp_code(phone_number, code)
        except Exception as exc:  # noqa: BLE001 — ne jamais faire échouer la réponse (anti-énumération)
            logger.warning("Envoi OTP reset par téléphone échoué | user=%s | error=%s", user.id, str(exc))

    async def verify_reset_code_phone(self, phone_number: str, code: str, code_repository) -> str:
        """Vérifie le code OTP (flow téléphone) et retourne un reset_token JWT."""
        user = await self.user_repository.get_by_phone(phone_number)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Compte introuvable ou inactif.",
            )

        entry = await code_repository.get_valid(user.id, code)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code invalide ou expiré.",
            )

        await code_repository.mark_used(entry.id)
        return SecurityUtils.create_reset_token(user.id)

    async def send_phone_verification_code(self, phone_number: str, code_repository) -> None:
        """Envoie un code OTP pour vérifier qu'un numéro appartient bien à la
        personne qui s'inscrit (aucun compte n'existe encore à ce stade)."""
        import random
        from datetime import timedelta

        from src.core.entities.phone_verification_code import PhoneVerificationCode
        from src.infrastructure.security.brute_force import brute_force_guard
        from src.infrastructure.security.field_encryption import get_encryptor
        from src.infrastructure.services.whatsapp_service import WhatsAppService

        identifier = f"phone-otp-send:{phone_number}"
        is_locked, remaining = await brute_force_guard.check_locked(identifier)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de demandes de code. Réessayez dans {remaining} secondes.",
                headers={"Retry-After": str(remaining)},
            )
        await brute_force_guard.record_failure(identifier)

        phone_hmac = get_encryptor().hmac_index(phone_number)
        await code_repository.delete_for_phone_hmac(phone_hmac)
        await code_repository.delete_expired()

        code = f"{random.randint(0, 999999):06d}"
        expires_at = utc_now() + timedelta(minutes=15)
        entry = PhoneVerificationCode(phone_hmac=phone_hmac, code=code, expires_at=expires_at)
        await code_repository.create(entry)

        try:
            await WhatsAppService().send_otp_code(phone_number, code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Envoi OTP vérification téléphone échoué | phone=%s | error=%s", phone_number, str(exc))

    async def verify_phone_code(self, phone_number: str, code: str, code_repository) -> str:
        """Vérifie le code OTP et retourne un jeton opaque à fournir à /auth/register."""
        import secrets

        from src.infrastructure.security.brute_force import brute_force_guard
        from src.infrastructure.security.field_encryption import get_encryptor

        identifier = f"phone-otp-verify:{phone_number}"
        is_locked, remaining = await brute_force_guard.check_locked(identifier)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de tentatives. Réessayez dans {remaining} secondes.",
                headers={"Retry-After": str(remaining)},
            )

        phone_hmac = get_encryptor().hmac_index(phone_number)
        entry = await code_repository.get_valid_by_phone_hmac(phone_hmac, code)
        if not entry:
            await brute_force_guard.record_failure(identifier)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code invalide ou expiré.",
            )

        await brute_force_guard.record_success(identifier)
        token = secrets.token_urlsafe(24)
        await code_repository.mark_verified(entry.id, token)
        return token

    async def forgot_password(self, email: str, email_service) -> None:
        user = await self.user_repository.get_by_email(email)
        if not user or not user.is_active:
            # Return silently to prevent email enumeration
            return

        reset_token = SecurityUtils.create_reset_token(user.id)
        await email_service.send_reset_password_email(
            to_email=user.email,
            token=reset_token,
            user_first_name=user.first_name or "Utilisateur",
        )

    async def reset_password(self, token: str, new_password: str, email_service=None) -> None:
        import time as _time

        import jwt

        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.security.token_blacklist import token_blacklist

        settings = get_settings()

        credentials_exception = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de réinitialisation est invalide ou a expiré. Veuillez refaire une demande.",
        )
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            sub: str = payload.get("sub")
            token_type: str = payload.get("type")
            jti: str | None = payload.get("jti")
            exp: float = float(payload.get("exp", _time.time()))
            if sub is None or token_type != "reset":
                raise credentials_exception
            user_id = UUID(sub)
        except (jwt.PyJWTError, ValueError):
            raise credentials_exception

        if jti and await token_blacklist.is_revoked(jti):
            raise credentials_exception

        user = await self.user_repository.get(user_id)
        if not user or not user.is_active:
            raise credentials_exception

        hashed_password = SecurityUtils.get_password_hash(new_password)
        user.hashed_password = hashed_password
        await self.user_repository.update(user.id, user)

        if jti:
            await token_blacklist.revoke(jti, exp)

        # Envoyer un email de confirmation de changement de mot de passe
        if email_service:
            try:
                await email_service.send_password_changed_email(
                    to_email=user.email,
                    user_first_name=user.first_name or "Utilisateur",
                )
            except Exception as exc:
                logger.warning(
                    "Password changed confirmation email failed | user_id=%s | email=%s | error=%s",
                    str(user.id),
                    user.email,
                    str(exc),
                )
