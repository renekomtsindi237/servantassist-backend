from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.user import User, UserRole
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.token_blacklist import token_blacklist
from src.presentation.schemas.auth import TokenData

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Decode JWT, extract user_id + role, and fetch user from DB."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_type: str | None = payload.get("type")
        if token_type is not None:
            raise credentials_exception
        sub: str = payload.get("sub")
        role: str = payload.get("role")
        jti: str | None = payload.get("jti")
        if sub is None or role is None:
            raise credentials_exception
        token_data = TokenData(user_id=sub, role=role)
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception

    # Vérifier que le token n'a pas été révoqué (logout ou rotation)
    if jti and await token_blacklist.is_revoked(jti):
        raise credentials_exception

    user_repo = UserRepository(session)
    user = await user_repo.get(token_data.user_id)
    if user is None:
        raise credentials_exception

    # Vérification de cohérence : le rôle du JWT doit correspondre au rôle en
    # BDD
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

    from src.infrastructure.repositories.responsable_repository import (
        NominationRepository,
    )

    nom_repo = NominationRepository(session)
    nominations = await nom_repo.get_active_by_user(current_user.id)
    if not nominations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'occupez aucun poste de responsable.",
        )
    return current_user


def get_require_poste(required_poste: str):
    """
    Factory pour créer une dépendance qui vérifie un poste spécifique.

    Usage :
    ```python
    @router.post("/")
    async def action(
        current_user = Depends(get_require_poste("ECONOME")),
        session = Depends(get_db_session)
    ):
        # L'utilisateur est soit ADMIN/AUMÔNIER, soit un SERVANT
        # avec une nomination ACTIVE au poste ECONOME
    ```
    """

    async def require_poste(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        """
        Vérifie qu'un utilisateur a le poste requis.

        Logique :
        1. ADMIN/AUMÔNIER : Accès toujours autorisé
        2. SERVANT : Doit avoir une nomination ACTIVE au poste requis
        3. Autres : Accès refusé
        """
        # ADMIN et AUMÔNIER ont accès à tout
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        # Vérifier que c'est un SERVANT
        if current_user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez être {required_poste} pour accéder à cette ressource.",
            )

        # Vérifier la nomination ACTIVE au poste requis
        from src.core.entities.responsable import PosteResponsable
        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nomination = await nom_repo.get_active_by_user(current_user.id)

        if not nomination:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez être nominé au poste {required_poste} pour effectuer cette action.",
            )

        # Vérifier que le poste correspond
        if nomination.poste.value != required_poste:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez être {required_poste}, vous êtes actuellement {nomination.poste.value}.",
            )

        return current_user

    return require_poste


# ═══════════════════════════════════════════════════════════════════════════
#  Dépendances spécifiques par poste de responsable
# ═══════════════════════════════════════════════════════════════════════════


# CHARGE_LITURGIE - Formations et spiritualité
def get_require_charge_liturgie():
    """Accepte CHARGE_LITURGIE ou CHARGE_LITURGIE_ADJOINT via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CHARGE_LITURGIE", "CHARGE_LITURGIE_ADJOINT")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Vous devez être CHARGE_LITURGIE, vous êtes {roles}")
            raise HTTPException(403, "Vous devez être nominé à CHARGE_LITURGIE")

        return current_user

    return require


require_charge_liturgie = get_require_charge_liturgie()


# CHARGE_SPORT_CULTURE - Activités sportives et culturelles
def get_require_sport_culture():
    """Accepte CHARGE_SPORT_CULTURE ou CHARGE_SPORT_CULTURE_ADJOINT via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CHARGE_SPORT_CULTURE", "CHARGE_SPORT_CULTURE_ADJOINT")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Vous devez être CHARGE_SPORT_CULTURE, vous êtes {roles}")
            raise HTTPException(403, "Vous devez être nominé à CHARGE_SPORT_CULTURE")

        return current_user

    return require


require_sport_culture = get_require_sport_culture()


# Alternative : require_charge_sport_culture (alias)
require_charge_sport_culture = require_sport_culture


# INTENDANT - Gestion matérielle et logistique
def get_require_intendant():
    """Accepte INTENDANT ou INTENDANT_ADJOINT via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("INTENDANT", "INTENDANT_ADJOINT")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Vous devez être INTENDANT, vous êtes {roles}")
            raise HTTPException(403, "Vous devez être nominé à INTENDANT")

        return current_user

    return require


require_intendant = get_require_intendant()


# DELEGUE/VICE_DELEGUE - Gestion générale et événements
def get_require_delegue():
    """Accepte DELEGUE ou VICE_DELEGUE via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("DELEGUE", "VICE_DELEGUE")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Vous devez être DELEGUE, vous êtes {roles}")
            raise HTTPException(403, "Vous devez être nominé à DELEGUE")

        return current_user

    return require


require_delegue = get_require_delegue()


# COMMISSAIRE_AUX_COMPTES - Audit financier
def get_require_commissaire():
    """Accepte COMMISSAIRE_AUX_COMPTES via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        if not nominations or not any(n.poste.value == "COMMISSAIRE_AUX_COMPTES" for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Vous devez être COMMISSAIRE_AUX_COMPTES, vous êtes {roles}")
            raise HTTPException(403, "Vous devez être nominé à COMMISSAIRE_AUX_COMPTES")

        return current_user

    return require


require_commissaire = get_require_commissaire()


def get_require_commissaire_strict():
    """Strictement COMMISSAIRE_AUX_COMPTES via nomination active. ADMIN/AUMÔNIER exclus."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="Accès réservé au Commissaire aux Comptes")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        if not nominations or not any(n.poste.value == "COMMISSAIRE_AUX_COMPTES" for n in nominations):
            raise HTTPException(403, "Accès réservé au Commissaire aux Comptes")

        return current_user

    return require


require_commissaire_strict = get_require_commissaire_strict()


# DELEGUE or SG - Management of Council Meetings
def get_require_delegue_or_sg():
    """Accepte DELEGUE, VICE_DELEGUE ou SECRETAIRE_GENERAL via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("DELEGUE", "VICE_DELEGUE", "SECRETAIRE_GENERAL")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès réservé au Délégué ou Secrétaire. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé au Délégué ou Secrétaire")

        return current_user

    return require


require_delegue_or_sg = get_require_delegue_or_sg()


# CENSEUR - Discipline and Attendance
def get_require_censeur():
    """Accepte CENSEUR ou CENSEUR_ADJOINT via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CENSEUR", "CENSEUR_ADJOINT")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès réservé au Censeur. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé au Censeur")

        return current_user

    return require


require_censeur = get_require_censeur()


# CENSEUR STRICT - Attendance Session Creation (EXCLUSIVE - no
# Admin/Aumônier bypass)
def get_require_censeur_strict():
    """
    Strictement CENSEUR ou CENSEUR_ADJOINT via nomination active.
    ADMIN/AUMÔNIER ne peuvent PAS creator des sessions d'appel.
    """

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        # STRICT : Les administrateurs ne pueden pas non plus
        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="Seul un CENSEUR peut effectuer cette action")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CENSEUR", "CENSEUR_ADJOINT")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès réservé au Censeur. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé au Censeur")

        return current_user

    return require


require_censeur_strict = get_require_censeur_strict()


# CONSEIL DE DISCIPLINE — vote collegial (Art. 16-17, strict, sans bypass
# Admin/Aumônier : ils supervisent le conseil mais n'y siegent pas).
def get_require_discipline_council_member():
    """Accepte uniquement les 7 sieges du conseil de discipline (via nomination active)."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=403,
                detail="Seul un membre du conseil de discipline peut voter.",
            )

        from src.core.entities.discipline import COUNCIL_POSTES
        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = {p.value for p in COUNCIL_POSTES}
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Vous n'occupez pas un siège du conseil de discipline.",
            )

        return current_user

    return require


require_discipline_council_member = get_require_discipline_council_member()


# ECONOME - Financial Management
def get_require_econome():
    """Accepte ECONOME via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        if not nominations or not any(n.poste.value == "ECONOME" for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès réservé à l'Econome. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé à l'Econome")

        return current_user

    return require


require_econome = get_require_econome()


# SECRETAIRE - Reports and Communication
def get_require_secretaire():
    """Accepte SECRETAIRE, SECRETAIRE_ADJOINT, SECRETAIRE_GENERAL ou SECRETAIRE_GENERAL_ADJOINT via nomination active."""  # noqa: E501

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        # Admin and Aumonier are EXCLUDED from report creation per security
        # requirements

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = (
            "SECRETAIRE_GENERAL",
            "SECRETAIRE_GENERAL_ADJOINT",
            "SECRETAIRE",
            "SECRETAIRE_ADJOINT",
        )
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès réservé au Secrétaire. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé au Secrétaire")

        return current_user

    return require


require_secretaire = get_require_secretaire()


# CONVOCATION DES PARENTS — Censeur, Secretariat, ou Admin/Aumonier (Art. 48-49)
def get_require_convocation_manager():
    """Accepte CENSEUR(_ADJOINT), SECRETAIRE(_GENERAL)(_ADJOINT) via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = (
            "CENSEUR",
            "CENSEUR_ADJOINT",
            "SECRETAIRE_GENERAL",
            "SECRETAIRE_GENERAL_ADJOINT",
            "SECRETAIRE",
            "SECRETAIRE_ADJOINT",
        )
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Accès réservé au Censeur, au Secrétariat, ou à l'Aumônier/Admin.",
            )

        return current_user

    return require


require_convocation_manager = get_require_convocation_manager()


# OUVERTURE DE DOSSIER DISCIPLINAIRE — Censeur, Ceremoniaire (Art. 41 : trouble
# durant la celebration eucharistique), ou Admin/Aumonier.
def get_require_open_discipline_case():
    """Accepte CENSEUR(_ADJOINT) ou CEREMONIAIRE via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CENSEUR", "CENSEUR_ADJOINT", "CEREMONIAIRE")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Accès réservé au Censeur, au Cérémoniaire, ou à l'Aumônier/Admin.",
            )

        return current_user

    return require


require_open_discipline_case = get_require_open_discipline_case()


# CONVOCATION AU CONSEIL DE DISCIPLINE — Censeur, ou Delegue/Vice-Delegue
# (Art. 16 : "il se reunit sous convocation du responsable Delegue"), ou Admin/Aumonier.
def get_require_convoke_discipline():
    """Accepte CENSEUR(_ADJOINT) ou DELEGUE(_VICE) via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CENSEUR", "CENSEUR_ADJOINT", "DELEGUE", "VICE_DELEGUE")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Accès réservé au Censeur, au Délégué, ou à l'Aumônier/Admin.",
            )

        return current_user

    return require


require_convoke_discipline = get_require_convoke_discipline()


# COMMUNICATION — Secretariat (Art. 8d : transmission des informations aux
# servants), ou Admin/Aumonier. Contrairement a require_secretaire (reserve
# aux rapports, Admin/Aumonier explicitement exclus), ici Admin/Aumonier
# gardent l'acces existant en plus du Secretariat.
def get_require_secretariat_or_admin():
    """Accepte SECRETAIRE(_GENERAL)(_ADJOINT) via nomination active, ou ADMIN/AUMÔNIER."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = (
            "SECRETAIRE_GENERAL",
            "SECRETAIRE_GENERAL_ADJOINT",
            "SECRETAIRE",
            "SECRETAIRE_ADJOINT",
        )
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Accès réservé au Secrétariat, ou à l'Aumônier/Admin.",
            )

        return current_user

    return require


require_secretariat_or_admin = get_require_secretariat_or_admin()


# RENDU DE VERDICT DISCIPLINAIRE — Aumonier (tout type de sanction) ou un
# poste habilite selon le type de sanction demande (voir
# DisciplineService.RENDER_VERDICT_SANCTION_SCOPE pour le detail par poste,
# Art. 39-44 punitions et Art. 51 radiation). Cette dependance ne fait que
# verifier qu'un poste pertinent existe ; le controle fin par type de
# sanction est fait cote service.
def get_require_verdict_authority():
    """Accepte AUMÔNIER, ou CENSEUR(_ADJOINT)/SECRETAIRE_GENERAL/CEREMONIAIRE via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role == UserRole.AUMÔNIER:
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=403,
                detail="Seul l'Aumônier ou un responsable habilité peut rendre un verdict.",
            )

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed = ("CENSEUR", "CENSEUR_ADJOINT", "SECRETAIRE_GENERAL", "CEREMONIAIRE")
        if not nominations or not any(n.poste.value in allowed for n in nominations):
            raise HTTPException(
                status_code=403,
                detail="Seul l'Aumônier ou un responsable habilité peut rendre un verdict.",
            )

        return current_user

    return require


require_verdict_authority = get_require_verdict_authority()

# Aliases for compatibility
require_econome_or_admin = require_econome
require_censeur_or_admin = require_censeur


async def validate_ws_token(token: str, session: AsyncSession) -> User:
    """
    Valide un JWT passé en query param pour les connexions WebSocket.

    Raises:
        Exception si le token est invalide ou l'utilisateur introuvable/inactif.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_type: str | None = payload.get("type")
        if token_type is not None:
            raise ValueError("Invalid token type")
        sub: str = payload.get("sub")
        if sub is None:
            raise ValueError("Missing sub claim")
        user_id = UUID(sub)
    except (jwt.PyJWTError, ValidationError, ValueError) as exc:
        raise Exception("Invalid token") from exc

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if user is None or not user.is_active:
        raise Exception("User not found or inactive")
    return user


# CHARGE_CLASSEMENT_DIMANCHE
def get_current_charge_classement_dimanche():
    """Accepte CHARGE_CLASSEMENT_DIMANCHE via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        if not nominations or not any(n.poste.value == "CHARGE_CLASSEMENT_DIMANCHE" for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(
                    403,
                    f"Accès réservé au Chargé de Classement Dimanche. Vous êtes {roles}",
                )
            raise HTTPException(403, "Accès réservé au Chargé de Classement Dimanche")

        return current_user

    return require


get_current_charge_classement_dimanche = get_current_charge_classement_dimanche()


# CHARGE_CLASSEMENT_SEMAINE
def get_current_charge_classement_semaine():
    """Accepte CHARGE_CLASSEMENT_SEMAINE via nomination active."""

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        if not nominations or not any(n.poste.value == "CHARGE_CLASSEMENT_SEMAINE" for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(
                    403,
                    f"Accès réservé au Chargé de Classement Semaine. Vous êtes {roles}",
                )
            raise HTTPException(403, "Accès réservé au Chargé de Classement Semaine")

        return current_user

    return require


get_current_charge_classement_semaine = get_current_charge_classement_semaine()


# SUNDAY_SCHEDULE History Access
def get_sunday_schedule_history_access():
    """
    Accepte ADMIN, AUMÔNIER, CHARGE_CLASSEMENT_DIMANCHE, CENSEUR, CENSEUR_ADJOINT.
    Utilisé pour consulter l'historique des modifications.
    """

    async def require(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
            return current_user

        if current_user.role != UserRole.SERVANT:
            raise HTTPException(status_code=403, detail="You must be a SERVANT")

        from src.infrastructure.repositories.responsable_repository import (
            NominationRepository,
        )

        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)

        allowed_postes = (
            "CHARGE_CLASSEMENT_DIMANCHE",
            "CENSEUR",
            "CENSEUR_ADJOINT",
        )
        if not nominations or not any(n.poste.value in allowed_postes for n in nominations):
            if nominations:
                roles = ", ".join([n.poste.value for n in nominations])
                raise HTTPException(403, f"Accès refusé. Vous êtes {roles}")
            raise HTTPException(403, "Accès réservé aux responsables autorisés")

        return current_user

    return require


get_sunday_schedule_history_access = get_sunday_schedule_history_access()
