"""
Unit tests for nomination-based auth dependencies in auth_deps.py.
Tests require_delegue, require_commissaire, require_commissaire_strict,
require_delegue_or_sg, require_censeur, require_censeur_strict,
require_econome, require_secretaire, get_current_charge_classement_dimanche,
get_current_charge_classement_semaine, get_sunday_schedule_history_access,
validate_ws_token.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_user(role_value):
    from src.core.entities.user import UserRole

    user = MagicMock()
    user.id = uuid4()
    user.is_active = True
    user.role = {
        "ADMIN": UserRole.ADMIN,
        "AUMONIER": UserRole.AUMÔNIER,
        "SERVANT": UserRole.SERVANT,
        "PARENT": UserRole.PARENT,
    }.get(role_value, UserRole.SERVANT)
    return user


def _make_nomination(poste_value):
    nom = MagicMock()
    nom.poste = MagicMock()
    nom.poste.value = poste_value
    return nom


def _mock_session():
    return AsyncMock()


# ─────────────────────────────────────────────────────────────────────────────
#  Helper: get the inner "require" function from a dependency factory
# ─────────────────────────────────────────────────────────────────────────────


def _get_require_delegue():
    from src.presentation.dependencies.auth_deps import get_require_delegue

    return get_require_delegue()


def _get_require_commissaire():
    from src.presentation.dependencies.auth_deps import get_require_commissaire

    return get_require_commissaire()


def _get_require_commissaire_strict():
    from src.presentation.dependencies.auth_deps import get_require_commissaire_strict

    return get_require_commissaire_strict()


def _get_require_delegue_or_sg():
    from src.presentation.dependencies.auth_deps import get_require_delegue_or_sg

    return get_require_delegue_or_sg()


def _get_require_censeur():
    from src.presentation.dependencies.auth_deps import get_require_censeur

    return get_require_censeur()


def _get_require_censeur_strict():
    from src.presentation.dependencies.auth_deps import get_require_censeur_strict

    return get_require_censeur_strict()


def _get_require_econome():
    from src.presentation.dependencies.auth_deps import get_require_econome

    return get_require_econome()


def _get_require_secretaire():
    from src.presentation.dependencies.auth_deps import get_require_secretaire

    return get_require_secretaire()


# ─────────────────────────────────────────────────────────────────────────────
#  require_delegue
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_delegue_admin_bypass():
    require = _get_require_delegue()
    user = _make_user("ADMIN")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_delegue_aumonier_bypass():
    require = _get_require_delegue()
    user = _make_user("AUMONIER")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_delegue_non_servant_raises():
    from fastapi import HTTPException

    require = _get_require_delegue()
    user = _make_user("PARENT")

    with pytest.raises(HTTPException) as exc:
        await require(current_user=user, session=_mock_session())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_delegue_servant_with_delegation():
    require = _get_require_delegue()
    user = _make_user("SERVANT")
    nom = _make_nomination("DELEGUE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_delegue_servant_no_nominations():
    from fastapi import HTTPException

    require = _get_require_delegue()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_delegue_servant_wrong_role():
    from fastapi import HTTPException

    require = _get_require_delegue()
    user = _make_user("SERVANT")
    nom = _make_nomination("ECONOME")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_commissaire
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_commissaire_admin_bypass():
    require = _get_require_commissaire()
    user = _make_user("ADMIN")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_commissaire_servant_success():
    require = _get_require_commissaire()
    user = _make_user("SERVANT")
    nom = _make_nomination("COMMISSAIRE_AUX_COMPTES")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_commissaire_servant_no_nom():
    from fastapi import HTTPException

    require = _get_require_commissaire()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_commissaire_servant_wrong_role():
    from fastapi import HTTPException

    require = _get_require_commissaire()
    user = _make_user("SERVANT")
    nom = _make_nomination("DELEGUE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_commissaire_strict
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_commissaire_strict_non_servant_raises():
    from fastapi import HTTPException

    require = _get_require_commissaire_strict()
    user = _make_user("ADMIN")

    with pytest.raises(HTTPException) as exc:
        await require(current_user=user, session=_mock_session())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_commissaire_strict_servant_success():
    require = _get_require_commissaire_strict()
    user = _make_user("SERVANT")
    nom = _make_nomination("COMMISSAIRE_AUX_COMPTES")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_commissaire_strict_no_nom():
    from fastapi import HTTPException

    require = _get_require_commissaire_strict()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_delegue_or_sg
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_delegue_or_sg_admin_bypass():
    require = _get_require_delegue_or_sg()
    user = _make_user("ADMIN")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_delegue_or_sg_secretaire_general_success():
    require = _get_require_delegue_or_sg()
    user = _make_user("SERVANT")
    nom = _make_nomination("SECRETAIRE_GENERAL")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_delegue_or_sg_no_nom():
    from fastapi import HTTPException

    require = _get_require_delegue_or_sg()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_censeur
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_censeur_admin_bypass():
    require = _get_require_censeur()
    user = _make_user("ADMIN")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_censeur_servant_success():
    require = _get_require_censeur()
    user = _make_user("SERVANT")
    nom = _make_nomination("CENSEUR")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_censeur_adjoint_success():
    require = _get_require_censeur()
    user = _make_user("SERVANT")
    nom = _make_nomination("CENSEUR_ADJOINT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_censeur_wrong_role():
    from fastapi import HTTPException

    require = _get_require_censeur()
    user = _make_user("SERVANT")
    nom = _make_nomination("DELEGUE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_censeur_strict
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_censeur_strict_non_servant_raises():
    from fastapi import HTTPException

    require = _get_require_censeur_strict()
    user = _make_user("ADMIN")

    with pytest.raises(HTTPException) as exc:
        await require(current_user=user, session=_mock_session())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_censeur_strict_servant_success():
    require = _get_require_censeur_strict()
    user = _make_user("SERVANT")
    nom = _make_nomination("CENSEUR")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_censeur_strict_no_nom():
    from fastapi import HTTPException

    require = _get_require_censeur_strict()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_econome
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_econome_admin_bypass():
    require = _get_require_econome()
    user = _make_user("ADMIN")
    result = await require(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_require_econome_servant_success():
    require = _get_require_econome()
    user = _make_user("SERVANT")
    nom = _make_nomination("ECONOME")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_econome_no_nom():
    from fastapi import HTTPException

    require = _get_require_econome()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_econome_wrong_role():
    from fastapi import HTTPException

    require = _get_require_econome()
    user = _make_user("SERVANT")
    nom = _make_nomination("CENSEUR")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  require_secretaire
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_secretaire_non_servant_raises():
    from fastapi import HTTPException

    require = _get_require_secretaire()
    user = _make_user("PARENT")

    with pytest.raises(HTTPException) as exc:
        await require(current_user=user, session=_mock_session())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_secretaire_servant_success():
    require = _get_require_secretaire()
    user = _make_user("SERVANT")
    nom = _make_nomination("SECRETAIRE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_secretaire_adjoint_success():
    require = _get_require_secretaire()
    user = _make_user("SERVANT")
    nom = _make_nomination("SECRETAIRE_ADJOINT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await require(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_require_secretaire_no_nom():
    from fastapi import HTTPException

    require = _get_require_secretaire()
    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_secretaire_wrong_role():
    from fastapi import HTTPException

    require = _get_require_secretaire()
    user = _make_user("SERVANT")
    nom = _make_nomination("ECONOME")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await require(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  get_current_charge_classement_dimanche / semaine
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_charge_classement_dimanche_admin_bypass():
    # call the factory again to get a fresh require
    from importlib import import_module

    # The function has been reassigned by calling the factory — need the factory
    from src.presentation.dependencies.auth_deps import get_current_charge_classement_dimanche
    from src.presentation.dependencies.auth_deps import get_current_charge_classement_dimanche as factory

    auth_deps = import_module("src.presentation.dependencies.auth_deps")

    # We already have the dependency installed
    user = _make_user("ADMIN")
    result = await auth_deps.get_current_charge_classement_dimanche(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_charge_classement_dimanche_servant_success():
    import importlib

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    nom = _make_nomination("CHARGE_CLASSEMENT_DIMANCHE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await auth_deps.get_current_charge_classement_dimanche(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_charge_classement_dimanche_no_nom():
    import importlib

    from fastapi import HTTPException

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await auth_deps.get_current_charge_classement_dimanche(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_charge_classement_semaine_admin_bypass():
    import importlib

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("ADMIN")
    result = await auth_deps.get_current_charge_classement_semaine(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_charge_classement_semaine_servant_success():
    import importlib

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    nom = _make_nomination("CHARGE_CLASSEMENT_SEMAINE")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await auth_deps.get_current_charge_classement_semaine(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_charge_classement_semaine_no_nom():
    import importlib

    from fastapi import HTTPException

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await auth_deps.get_current_charge_classement_semaine(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  get_sunday_schedule_history_access
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_history_admin_bypass():
    import importlib

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("ADMIN")
    result = await auth_deps.get_sunday_schedule_history_access(current_user=user, session=_mock_session())
    assert result is user


@pytest.mark.asyncio
async def test_sunday_history_servant_censeur_success():
    import importlib

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    nom = _make_nomination("CENSEUR")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        result = await auth_deps.get_sunday_schedule_history_access(current_user=user, session=session)

    assert result is user


@pytest.mark.asyncio
async def test_sunday_history_no_nom():
    import importlib

    from fastapi import HTTPException

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await auth_deps.get_sunday_schedule_history_access(current_user=user, session=session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_sunday_history_wrong_nom():
    import importlib

    from fastapi import HTTPException

    auth_deps = importlib.import_module("src.presentation.dependencies.auth_deps")

    user = _make_user("SERVANT")
    nom = _make_nomination("ECONOME")
    session = _mock_session()

    mock_repo = AsyncMock()
    mock_repo.get_active_by_user = AsyncMock(return_value=[nom])

    with patch("src.infrastructure.repositories.responsable_repository.NominationRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc:
            await auth_deps.get_sunday_schedule_history_access(current_user=user, session=session)
    assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
#  validate_ws_token
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_ws_token_invalid_jwt():
    from src.presentation.dependencies.auth_deps import validate_ws_token

    session = _mock_session()
    with pytest.raises(Exception, match="Invalid token"):
        await validate_ws_token("not-a-jwt", session)


@pytest.mark.asyncio
async def test_validate_ws_token_user_not_found():
    from src.presentation.dependencies.auth_deps import validate_ws_token

    session = _mock_session()

    import jwt

    from src.infrastructure.config.settings import get_settings

    settings = get_settings()

    token = jwt.encode({"sub": str(uuid4())}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=None)

    with patch("src.presentation.dependencies.auth_deps.UserRepository", return_value=mock_repo):
        with pytest.raises(Exception, match="User not found or inactive"):
            await validate_ws_token(token, session)


@pytest.mark.asyncio
async def test_validate_ws_token_inactive_user():
    from src.presentation.dependencies.auth_deps import validate_ws_token

    session = _mock_session()

    import jwt

    from src.infrastructure.config.settings import get_settings

    settings = get_settings()

    token = jwt.encode({"sub": str(uuid4())}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    inactive_user = MagicMock()
    inactive_user.is_active = False
    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=inactive_user)

    with patch("src.presentation.dependencies.auth_deps.UserRepository", return_value=mock_repo):
        with pytest.raises(Exception, match="User not found or inactive"):
            await validate_ws_token(token, session)


@pytest.mark.asyncio
async def test_validate_ws_token_success():
    from src.presentation.dependencies.auth_deps import validate_ws_token

    session = _mock_session()

    import jwt

    from src.infrastructure.config.settings import get_settings

    settings = get_settings()

    token = jwt.encode({"sub": str(uuid4())}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    active_user = MagicMock()
    active_user.is_active = True
    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=active_user)

    with patch("src.presentation.dependencies.auth_deps.UserRepository", return_value=mock_repo):
        result = await validate_ws_token(token, session)

    assert result is active_user
