import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.core.entities.user import UserRole
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.invitation_repository import InvitationCodeRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.brute_force import brute_force_guard
from src.infrastructure.security.token_blacklist import token_blacklist
from src.presentation.dependencies.auth_deps import get_current_active_user
from src.presentation.schemas.auth import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    RequestResetCodeRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserCreateWithInvite,
    UserLogin,
    UserPhoneLogin,
    UserResponse,
    VerifyResetCodeRequest,
    VerifyResetCodeResponse,
)

router = APIRouter()

# Roles autorises pour l'auto-inscription publique
_SELF_REGISTER_ROLES = {UserRole.SERVANT, UserRole.PARENT}


async def _check_brute_force(identifier: str) -> None:
    """Verifie si l'identifiant est verrouille par la protection brute-force."""
    is_locked, remaining = await brute_force_guard.check_locked(identifier)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Compte temporairement bloqué suite à trop de tentatives échouées. Réessayez dans {remaining} secondes.",
            headers={"Retry-After": str(remaining)},
        )


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Login par **email + mot de passe** -- reserve aux roles **ADMIN** et **AUMONIER**.

    Utilise le format OAuth2 (username = email).
    """
    from pydantic import ValidationError as PydanticValidationError

    # -- Protection brute-force ------------------------------------
    identifier = form_data.username.lower().strip()
    await _check_brute_force(identifier)

    try:
        login_data = UserLogin(
    email=form_data.username,
     password=form_data.password)
    except PydanticValidationError:
        await brute_force_guard.record_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo)

    try:
        user = await auth_service.authenticate_user(login_data)
    except HTTPException:
        await brute_force_guard.record_failure(identifier)
        raise

    if not user:
        await brute_force_guard.record_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Connexion reussie : reinitialiser le compteur
    await brute_force_guard.record_success(identifier)
    return await auth_service.create_tokens(user)


@router.post("/login/phone", response_model=Token)
async def login_with_phone(
    login_data: UserPhoneLogin,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Login par **numero de telephone + mot de passe** -- reserve aux roles **PARENT** et **SERVANT**.

    Format telephone : +{indicatif}{numero} (ex. +237123456789)
    """
    # -- Protection brute-force ------------------------------------
    identifier = login_data.phone_number.strip()
    await _check_brute_force(identifier)

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo)

    try:
        user = await auth_service.authenticate_user(login_data)
    except HTTPException:
        await brute_force_guard.record_failure(identifier)
        raise

    # Connexion reussie : reinitialiser le compteur
    await brute_force_guard.record_success(identifier)
    return await auth_service.create_tokens(user)


@router.post("/register", response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreateWithInvite,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Inscription publique — **uniquement SERVANT et PARENT**.

    **Rôles et exigences :**
    - **SERVANT** : Auto-inscription (rôle par défaut, pas de code requis)
    - **PARENT** : Nécessite un `invitation_code` valide fourni par l'admin

    Les rôles ADMIN et AUMÔNIER ne peuvent **pas** s'inscrire ici.
    Ils sont créés exclusivement via les endpoints `/admin/*`.
    """
    # ── Filtrage en amont : seuls SERVANT et PARENT sont autorisés ──
    if user_data.role not in _SELF_REGISTER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Le rôle {user_data.role.value} ne peut pas s'inscrire publiquement. Contactez un administrateur.",
        )

    user_repo = UserRepository(session)
    invitation_repo = InvitationCodeRepository(session)
    auth_service = AuthService(user_repo, invitation_repo)

    return await auth_service.register_user(
        user_data,
        invitation_code=user_data.invitation_code,
        admin_id=None,  # Self-registration, no admin
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Renouveler les tokens JWT à partir d'un refresh_token valide."""
    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo)

    return await auth_service.refresh_token(request.refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: Annotated[object, Depends(get_current_active_user)],
):
    """
    Déconnecte l'utilisateur en révoquant le token d'accès courant.

    Le token est ajouté à la blacklist JTI jusqu'à son expiration.
    """
    _settings = get_settings()
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token manquant")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, _settings.JWT_SECRET_KEY, algorithms=[_settings.JWT_ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp", time.time() + 1800)
        if jti:
            await token_blacklist.revoke(jti, float(exp))
    except JWTError:
        pass  # Token déjà invalide, rien à faire

    return {"message": "Déconnecté avec succès."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Demander la réinitialisation du mot de passe.
    Retourne toujours 200 OK pour prévenir l'énumération d'emails.
    """
    from src.infrastructure.services.email_service import EmailService

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo)
    email_service = EmailService()

    await auth_service.forgot_password(request.email, email_service)
    return {"message": "Si cet e-mail est enregistré, un lien de réinitialisation vous a été envoyé."}


@router.post("/request-reset-code", status_code=status.HTTP_200_OK)
async def request_reset_code(
    request: RequestResetCodeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Envoie un code OTP 6 chiffres par email pour réinitialisation mobile.
    Retourne toujours 200 OK pour prévenir l'énumération d'emails.
    """
    from src.infrastructure.services.email_service import EmailService
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    user_repo = UserRepository(session)
    code_repo = PasswordResetCodeRepository(session)
    auth_service = AuthService(user_repo)
    email_service = EmailService()

    await auth_service.request_reset_code(request.email, code_repo, email_service)
    return {"message": "Si ce compte existe, un code a été envoyé par email."}


@router.post("/verify-reset-code", response_model=VerifyResetCodeResponse)
async def verify_reset_code(
    request: VerifyResetCodeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Vérifie le code OTP et retourne un reset_token JWT valable 15 minutes."""
    from src.infrastructure.repositories.password_reset_code_repository import PasswordResetCodeRepository

    user_repo = UserRepository(session)
    code_repo = PasswordResetCodeRepository(session)
    auth_service = AuthService(user_repo)

    reset_token = await auth_service.verify_reset_code(request.email, request.code, code_repo)
    return VerifyResetCodeResponse(reset_token=reset_token)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Réinitialiser le mot de passe avec un token valide."""
    from src.infrastructure.services.email_service import EmailService

    user_repo = UserRepository(session)
    auth_service = AuthService(user_repo)
    email_service = EmailService()

    await auth_service.reset_password(request.token, request.new_password, email_service)
    return {"message": "Votre mot de passe a été réinitialisé avec succès."}


@router.get(
    "/server-pubkey",
    summary="Clé publique EC du serveur (chiffrement de charge utile)",
    description=(
        "Retourne la clé publique EC P-256 du serveur en base64url (65 octets non-compressés). "
        "Les clients l'utilisent pour chiffrer les corps de requête via ECDH éphémère + AES-256-GCM "
        "(conformité Loi 2024/017 Cameroun). Endpoint public — aucune authentification requise."
    ),
    tags=["Authentication"],
)
async def get_server_pubkey():
    """Distribue la clé publique EC pour le chiffrement de charge utile."""
    settings = get_settings()
    if not settings.PAYLOAD_ENCRYPTION_PRIVATE_KEY:
        return {
            "key": None,
            "algorithm": "ECDH-P256-AES256GCM",
            "version": "1",
            "enabled": False,
        }
    from src.infrastructure.security.payload_encryption import get_payload_encryptor
    encryptor = get_payload_encryptor()
    return {
        "key": encryptor.public_key_b64,
        "algorithm": "ECDH-P256-AES256GCM",
        "version": "1",
        "enabled": True,
    }
