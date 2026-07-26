"""
Unit tests for src/presentation/dependencies/auth_deps.py

Tests cover:
- get_current_user: JWT decode, blacklist, user lookup, role mismatch
- get_current_active_user, get_current_admin_user, etc.
- Role-specific dependencies (admin, aumonier, servant, parent, responsable)
- get_require_poste factory
- Poste-specific dependencies: require_charge_liturgie, require_sport_culture, require_intendant
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.entities.user import User, UserRole

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_user(role: UserRole = UserRole.ADMIN, is_active: bool = True) -> User:
    return User(
        id=uuid4(),
        first_name="Test",
        last_name="User",
        email=f"{uuid4().hex[:6]}@test.com",
        role=role,
        is_active=is_active,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_active_user
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_active_user_active():
    from src.presentation.dependencies.auth_deps import get_current_active_user

    user = _make_user(is_active=True)
    result = await get_current_active_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    from src.presentation.dependencies.auth_deps import get_current_active_user

    user = _make_user(is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(user)
    assert exc_info.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_admin_user
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_admin_user_admin():
    from src.presentation.dependencies.auth_deps import get_current_admin_user

    user = _make_user(UserRole.ADMIN)
    result = await get_current_admin_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_admin_user_non_admin():
    from src.presentation.dependencies.auth_deps import get_current_admin_user

    user = _make_user(UserRole.SERVANT)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_user(user)
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_aumonier_user
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_aumonier_user_aumonier():
    from src.presentation.dependencies.auth_deps import get_current_aumonier_user

    user = _make_user(UserRole.AUMÔNIER)
    result = await get_current_aumonier_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_aumonier_user_non_aumonier():
    from src.presentation.dependencies.auth_deps import get_current_aumonier_user

    user = _make_user(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_aumonier_user(user)
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_admin_or_aumonier
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_admin_or_aumonier_admin():
    from src.presentation.dependencies.auth_deps import get_current_admin_or_aumonier

    user = _make_user(UserRole.ADMIN)
    result = await get_current_admin_or_aumonier(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_admin_or_aumonier_aumonier():
    from src.presentation.dependencies.auth_deps import get_current_admin_or_aumonier

    user = _make_user(UserRole.AUMÔNIER)
    result = await get_current_admin_or_aumonier(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_admin_or_aumonier_servant():
    from src.presentation.dependencies.auth_deps import get_current_admin_or_aumonier

    user = _make_user(UserRole.SERVANT)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin_or_aumonier(user)
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_parent_user
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_parent_user_parent():
    from src.presentation.dependencies.auth_deps import get_current_parent_user

    user = _make_user(UserRole.PARENT)
    result = await get_current_parent_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_parent_user_non_parent():
    from src.presentation.dependencies.auth_deps import get_current_parent_user

    user = _make_user(UserRole.SERVANT)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_parent_user(user)
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_servant_user
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_servant_user_servant():
    from src.presentation.dependencies.auth_deps import get_current_servant_user

    user = _make_user(UserRole.SERVANT)
    result = await get_current_servant_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_servant_user_non_servant():
    from src.presentation.dependencies.auth_deps import get_current_servant_user

    user = _make_user(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_servant_user(user)
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_responsable
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_responsable_admin():
    from src.presentation.dependencies.auth_deps import get_current_responsable

    user = _make_user(UserRole.ADMIN)
    result = await get_current_responsable(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_get_current_responsable_aumonier():
    from src.presentation.dependencies.auth_deps import get_current_responsable

    user = _make_user(UserRole.AUMÔNIER)
    result = await get_current_responsable(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_get_current_responsable_parent_forbidden():
    from src.presentation.dependencies.auth_deps import get_current_responsable

    user = _make_user(UserRole.PARENT)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_responsable(user, AsyncMock())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_responsable_servant_with_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import get_current_responsable

    user = _make_user(UserRole.SERVANT)
    session = AsyncMock()

    nomination = MagicMock()
    nomination.poste.value = "DELEGUE"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nomination])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        result = await get_current_responsable(user, session)

    assert result is user


@pytest.mark.asyncio
async def test_get_current_responsable_servant_without_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import get_current_responsable

    user = _make_user(UserRole.SERVANT)
    session = AsyncMock()

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_responsable(user, session)

    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_require_poste factory
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_require_poste_admin_passthrough():
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.ADMIN)
    result = await require_fn(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_get_require_poste_aumonier_passthrough():
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.AUMÔNIER)
    result = await require_fn(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_get_require_poste_parent_forbidden():
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.PARENT)

    with pytest.raises(HTTPException) as exc_info:
        await require_fn(user, AsyncMock())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_require_poste_servant_no_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.SERVANT)

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=None)

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_fn(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_require_poste_servant_wrong_poste():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.SERVANT)

    nomination = MagicMock()
    nomination.poste.value = "SECRETAIRE_GENERAL"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=nomination)

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_fn(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_require_poste_servant_correct_poste():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import get_require_poste

    require_fn = get_require_poste("ECONOME")
    user = _make_user(UserRole.SERVANT)

    nomination = MagicMock()
    nomination.poste.value = "ECONOME"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=nomination)

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        result = await require_fn(user, AsyncMock())

    assert result is user


# ═══════════════════════════════════════════════════════════════════════════════
#  require_charge_liturgie
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_require_charge_liturgie_admin():
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.ADMIN)
    result = await require_charge_liturgie(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_require_charge_liturgie_aumonier():
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.AUMÔNIER)
    result = await require_charge_liturgie(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_require_charge_liturgie_parent_forbidden():
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.PARENT)
    with pytest.raises(HTTPException) as exc_info:
        await require_charge_liturgie(user, AsyncMock())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_charge_liturgie_servant_with_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "CHARGE_LITURGIE"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        result = await require_charge_liturgie(user, AsyncMock())

    assert result is user


@pytest.mark.asyncio
async def test_require_charge_liturgie_servant_wrong_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "ECONOME"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_charge_liturgie(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_charge_liturgie_servant_no_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_charge_liturgie

    user = _make_user(UserRole.SERVANT)

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_charge_liturgie(user, AsyncMock())

    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  require_sport_culture
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_require_sport_culture_admin():
    from src.presentation.dependencies.auth_deps import require_sport_culture

    user = _make_user(UserRole.ADMIN)
    result = await require_sport_culture(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_require_sport_culture_servant_with_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_sport_culture

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "CHARGE_SPORT_CULTURE"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        result = await require_sport_culture(user, AsyncMock())

    assert result is user


@pytest.mark.asyncio
async def test_require_sport_culture_servant_no_nominations():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_sport_culture

    user = _make_user(UserRole.SERVANT)

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_sport_culture(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_sport_culture_parent_forbidden():
    from src.presentation.dependencies.auth_deps import require_sport_culture

    user = _make_user(UserRole.PARENT)
    with pytest.raises(HTTPException) as exc_info:
        await require_sport_culture(user, AsyncMock())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_sport_culture_servant_wrong_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_sport_culture

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "DELEGUE"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_sport_culture(user, AsyncMock())

    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  require_intendant
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_require_intendant_admin():
    from src.presentation.dependencies.auth_deps import require_intendant

    user = _make_user(UserRole.ADMIN)
    result = await require_intendant(user, AsyncMock())
    assert result is user


@pytest.mark.asyncio
async def test_require_intendant_servant_with_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_intendant

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "INTENDANT"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        result = await require_intendant(user, AsyncMock())

    assert result is user


@pytest.mark.asyncio
async def test_require_intendant_servant_wrong_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_intendant

    user = _make_user(UserRole.SERVANT)

    nom1 = MagicMock()
    nom1.poste.value = "ECONOME"

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[nom1])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_intendant(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_intendant_servant_no_nomination():
    import src.infrastructure.repositories.responsable_repository as nom_module
    from src.presentation.dependencies.auth_deps import require_intendant

    user = _make_user(UserRole.SERVANT)

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_intendant(user, AsyncMock())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_intendant_parent_forbidden():
    from src.presentation.dependencies.auth_deps import require_intendant

    user = _make_user(UserRole.PARENT)
    with pytest.raises(HTTPException) as exc_info:
        await require_intendant(user, AsyncMock())
    assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
#  get_current_user — JWT decoding
# ═══════════════════════════════════════════════════════════════════════════════


def _patch_get_current_user_deps(user_obj, blacklisted=False):
    """Context manager stack for get_current_user tests.

    auth_deps.py imports UserRepository at module level:
      from src.infrastructure.repositories.user_repository import UserRepository
    So we must patch it in the auth_deps namespace.
    """
    import src.infrastructure.security.token_blacklist as bl_module
    import src.presentation.dependencies.auth_deps as auth_deps_module

    mock_user_repo = MagicMock()
    mock_user_repo.get = AsyncMock(return_value=user_obj)

    mock_blacklist = MagicMock()
    mock_blacklist.is_revoked = AsyncMock(return_value=blacklisted)

    class _Ctx:
        def __enter__(self):
            self._p1 = patch.object(auth_deps_module, "UserRepository", return_value=mock_user_repo)
            # token_blacklist is imported at module level in auth_deps:
            # from src.infrastructure.security.token_blacklist import token_blacklist
            # So we patch in the auth_deps namespace, not the token_blacklist module.
            self._p2 = patch.object(auth_deps_module, "token_blacklist", mock_blacklist)
            self._p1.__enter__()
            self._p2.__enter__()
            return self

        def __exit__(self, *a):
            self._p2.__exit__(*a)
            self._p1.__exit__(*a)

    return _Ctx()


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    from src.presentation.dependencies.auth_deps import get_current_user

    user = _make_user(UserRole.SERVANT)
    payload = {"sub": str(user.id), "role": user.role.value, "jti": None}

    with patch("jwt.decode", return_value=payload):
        with _patch_get_current_user_deps(user, blacklisted=False):
            result = await get_current_user("fake_token", AsyncMock())

    assert result is user


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    import jwt as pyjwt

    from src.presentation.dependencies.auth_deps import get_current_user

    with patch("jwt.decode", side_effect=pyjwt.PyJWTError("bad token")):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_user_id_in_payload():
    from src.presentation.dependencies.auth_deps import get_current_user

    payload = {"sub": None, "role": "SERVANT", "jti": None}

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("fake_token", AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_refresh_token_rejected():
    """Tokens with type='refresh' should be rejected."""
    from src.presentation.dependencies.auth_deps import get_current_user

    payload = {"sub": str(uuid4()), "role": "SERVANT", "jti": "abc", "type": "refresh"}

    with patch("jwt.decode", return_value=payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("refresh_token", AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_blacklisted_token():
    from src.presentation.dependencies.auth_deps import get_current_user

    user = _make_user(UserRole.SERVANT)
    payload = {"sub": str(user.id), "role": user.role.value, "jti": "blacklisted-jti"}

    with patch("jwt.decode", return_value=payload):
        with _patch_get_current_user_deps(user, blacklisted=True):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("revoked_token", AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found_in_db():
    from src.presentation.dependencies.auth_deps import get_current_user

    payload = {"sub": str(uuid4()), "role": "SERVANT", "jti": None}

    with patch("jwt.decode", return_value=payload):
        with _patch_get_current_user_deps(None, blacklisted=False):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token", AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_role_mismatch():
    from src.presentation.dependencies.auth_deps import get_current_user

    user = _make_user(UserRole.ADMIN)  # DB says ADMIN
    # But token says SERVANT
    payload = {"sub": str(user.id), "role": "SERVANT", "jti": None}

    with patch("jwt.decode", return_value=payload):
        with _patch_get_current_user_deps(user, blacklisted=False):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token", AsyncMock())

    assert exc_info.value.status_code == 401
