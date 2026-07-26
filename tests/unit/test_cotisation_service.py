"""Unit tests for CotisationService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.cotisation_service import CotisationService
from src.core.entities.cotisation import (
    CotisationPeriod,
    CotisationStatus,
    CotisationType,
    MemberCotisation,
    PeriodType,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.cotisation import (
    CotisationPeriodCreate,
    CotisationPeriodUpdate,
    MemberCotisationCreate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
START = datetime(2026, 6, 1, 0, 0, 0)
END = datetime(2026, 6, 30, 0, 0, 0)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_period(is_active=True, amount_expected=5000.0, **kwargs) -> CotisationPeriod:
    return CotisationPeriod(
        id=kwargs.pop("id", uuid4()),
        title="Cotisation Juin 2026",
        cotisation_type=kwargs.pop("cotisation_type", CotisationType.ORDINAIRE),
        period_type=kwargs.pop("period_type", PeriodType.MENSUEL),
        amount_expected=amount_expected,
        start_date=kwargs.pop("start_date", START),
        end_date=kwargs.pop("end_date", END),
        is_active=is_active,
        created_by=kwargs.pop("created_by", uuid4()),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _make_payment(period_id=None, user_id=None, amount_paid=5000.0, **kwargs) -> MemberCotisation:
    return MemberCotisation(
        id=kwargs.pop("id", uuid4()),
        period_id=period_id or uuid4(),
        user_id=user_id or uuid4(),
        amount_paid=amount_paid,
        status=kwargs.pop("status", CotisationStatus.PAYE),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _make_user(role=UserRole.SERVANT) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Pierre",
        email="jean@test.com",
        hashed_password="x",
        role=role,
        created_at=NOW,
        updated_at=NOW,
    )


def _period_stats(total_members=5, total_paid=3, total_amount_collected=15000.0) -> dict:
    return {
        "total_members": total_members,
        "total_paid": total_paid,
        "total_amount_collected": total_amount_collected,
    }


def _enriched_payment(p: MemberCotisation) -> dict:
    return {
        "id": p.id,
        "period_id": p.period_id,
        "user_id": p.user_id,
        "amount_paid": p.amount_paid,
        "status": p.status,
        "payment_date": p.payment_date,
        "payment_method": p.payment_method,
        "notes": p.notes,
        "recorded_by": p.recorded_by,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "user_first_name": None,
        "user_last_name": None,
        "period_title": None,
        "amount_expected": None,
    }


def _make_svc(period_repo=None, payment_repo=None, user_repo=None, nomination_repo=None) -> CotisationService:
    if period_repo is None:
        period_repo = MagicMock()
        period_repo.create = AsyncMock()
        period_repo.get = AsyncMock(return_value=None)
        period_repo.update = AsyncMock()
        period_repo.delete = AsyncMock()
        period_repo.list_all = AsyncMock(return_value=([], 0))
        period_repo.list_ordinaire_since = AsyncMock(return_value=[])
    if payment_repo is None:
        payment_repo = MagicMock()
        payment_repo.create = AsyncMock()
        payment_repo.get = AsyncMock(return_value=None)
        payment_repo.update = AsyncMock()
        payment_repo.get_by_period_and_user = AsyncMock(return_value=None)
        payment_repo.get_overlapping_ordinaire_payment = AsyncMock(return_value=None)
        payment_repo.get_period_stats = AsyncMock(return_value=_period_stats())
        payment_repo.list_by_period = AsyncMock(return_value=[])
        payment_repo.list_by_user = AsyncMock(return_value=[])
        payment_repo.enrich_cotisation = AsyncMock(return_value={})
        payment_repo.enrich_cotisations = AsyncMock(return_value=[])
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
        user_repo.list_paginated = AsyncMock(return_value=([], 0))
    if nomination_repo is None:
        nomination_repo = MagicMock()
        nomination_repo.list_all_active = AsyncMock(return_value=[])
    return CotisationService(period_repo, payment_repo, user_repo, nomination_repo)


# ── create_period ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_period_end_before_start():
    svc = _make_svc()
    data = CotisationPeriodCreate(
        title="Cot Juin",
        amount_expected=5000,
        start_date=END,
        end_date=START,  # inverted
    )
    with pytest.raises(Exception) as exc:
        await svc.create_period(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_period_success():
    period = _make_period(cotisation_type=CotisationType.SPECIALE, amount_expected=5000)
    svc = _make_svc()
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    data = CotisationPeriodCreate(
        title="Camp spirituel",
        cotisation_type=CotisationType.SPECIALE,
        amount_expected=5000,
        start_date=START,
        end_date=END,
    )
    result = await svc.create_period(data, uuid4())
    assert result.id == period.id
    assert result.total_members == 5


@pytest.mark.asyncio
async def test_create_period_ordinaire_mensuel_wrong_amount_rejected():
    """Une cotisation ORDINAIRE/MENSUEL doit valoir exactement 500 FCFA (Art. 22)."""
    svc = _make_svc()
    data = CotisationPeriodCreate(
        title="Cotisation Juin",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.MENSUEL,
        amount_expected=400,
        start_date=START,
        end_date=END,
    )
    with pytest.raises(Exception) as exc:
        await svc.create_period(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_period_ordinaire_hebdomadaire_wrong_amount_rejected():
    """Une cotisation ORDINAIRE/HEBDOMADAIRE doit valoir exactement 100 FCFA (Art. 22)."""
    svc = _make_svc()
    data = CotisationPeriodCreate(
        title="Cotisation samedi",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.HEBDOMADAIRE,
        amount_expected=50,
        start_date=START,
        end_date=END,
    )
    with pytest.raises(Exception) as exc:
        await svc.create_period(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_period_ordinaire_mensuel_correct_amount_accepted():
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL, amount_expected=500)
    svc = _make_svc()
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    data = CotisationPeriodCreate(
        title="Cotisation Juin",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.MENSUEL,
        amount_expected=500,
        start_date=START,
        end_date=END,
    )
    result = await svc.create_period(data, uuid4())
    assert result.id == period.id


@pytest.mark.asyncio
async def test_create_period_ordinaire_hebdomadaire_correct_amount_accepted():
    period = _make_period(
        cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.HEBDOMADAIRE, amount_expected=100
    )
    svc = _make_svc()
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    data = CotisationPeriodCreate(
        title="Cotisation samedi",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.HEBDOMADAIRE,
        amount_expected=100,
        start_date=START,
        end_date=END,
    )
    result = await svc.create_period(data, uuid4())
    assert result.id == period.id


@pytest.mark.asyncio
async def test_create_period_aube_free_amount_accepted():
    """La cotisation AUBE (Art. 21) reste a montant libre."""
    period = _make_period(cotisation_type=CotisationType.AUBE, period_type=PeriodType.ANNUEL, amount_expected=3000)
    svc = _make_svc()
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    data = CotisationPeriodCreate(
        title="Cotisation aubes 2026",
        cotisation_type=CotisationType.AUBE,
        period_type=PeriodType.ANNUEL,
        amount_expected=3000,
        start_date=START,
        end_date=END,
    )
    result = await svc.create_period(data, uuid4())
    assert result.id == period.id


# ── create_period : obligation automatique (Art. 22, cotisation obligatoire) ─


def _make_nomination(user_id):
    n = MagicMock()
    n.user_id = user_id
    return n


@pytest.mark.asyncio
async def test_create_period_ordinaire_creates_obligations_for_non_responsables():
    """Chaque servant sans poste actif recoit une obligation EN_ATTENTE (Art. 22)."""
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL, amount_expected=500)
    servant_libre = _make_user()
    servant_responsable = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant_libre, servant_responsable], 2))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[_make_nomination(servant_responsable.id)])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    svc.payment_repo.get_by_period_and_user.return_value = None

    data = CotisationPeriodCreate(
        title="Cotisation Juin",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.MENSUEL,
        amount_expected=500,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    svc.payment_repo.create.assert_called_once()
    created_obligation = svc.payment_repo.create.call_args[0][0]
    assert created_obligation.user_id == servant_libre.id
    assert created_obligation.status == CotisationStatus.EN_ATTENTE
    assert created_obligation.amount_paid == 0


@pytest.mark.asyncio
async def test_create_period_ordinaire_skips_existing_obligation():
    """Si une obligation/paiement existe deja pour ce servant, pas de doublon."""
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL, amount_expected=500)
    servant = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant], 1))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    svc.payment_repo.get_by_period_and_user.return_value = _make_payment(period_id=period.id, user_id=servant.id)

    data = CotisationPeriodCreate(
        title="Cotisation Juin",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.MENSUEL,
        amount_expected=500,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    svc.payment_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_period_speciale_creates_obligations():
    """Art. 23 : camp spirituel/fete de fin d'annee sont obligatoires pour tous les servants."""
    period = _make_period(cotisation_type=CotisationType.SPECIALE, amount_expected=10000)
    servant = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant], 1))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    svc.payment_repo.get_by_period_and_user.return_value = None

    data = CotisationPeriodCreate(
        title="Camp spirituel",
        cotisation_type=CotisationType.SPECIALE,
        amount_expected=10000,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    svc.payment_repo.create.assert_called_once()
    created_obligation = svc.payment_repo.create.call_args[0][0]
    assert created_obligation.user_id == servant.id
    assert created_obligation.status == CotisationStatus.EN_ATTENTE


@pytest.mark.asyncio
async def test_create_period_aube_creates_obligations():
    """Art. 21 : la cotisation aube est obligatoire pour les nouveaux et les anciens."""
    period = _make_period(cotisation_type=CotisationType.AUBE, period_type=PeriodType.ANNUEL, amount_expected=3000)
    servant = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant], 1))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    svc.payment_repo.get_by_period_and_user.return_value = None

    data = CotisationPeriodCreate(
        title="Cotisation aubes 2026",
        cotisation_type=CotisationType.AUBE,
        period_type=PeriodType.ANNUEL,
        amount_expected=3000,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    svc.payment_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_period_amende_does_not_create_obligations():
    """Une AMENDE est individuelle (penalite ciblee) : pas d'obligation pour tous."""
    period = _make_period(cotisation_type=CotisationType.AMENDE, period_type=PeriodType.PONCTUEL, amount_expected=1000)
    servant = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant], 1))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()

    data = CotisationPeriodCreate(
        title="Amende",
        cotisation_type=CotisationType.AMENDE,
        period_type=PeriodType.PONCTUEL,
        amount_expected=1000,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    user_repo.list_paginated.assert_not_called()
    svc.payment_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_period_autre_does_not_create_obligations():
    """Une contribution AUTRE est volontaire : pas d'obligation automatique."""
    period = _make_period(cotisation_type=CotisationType.AUTRE, amount_expected=500)
    servant = _make_user()

    user_repo = MagicMock()
    user_repo.list_paginated = AsyncMock(return_value=([servant], 1))
    nomination_repo = MagicMock()
    nomination_repo.list_all_active = AsyncMock(return_value=[])

    svc = _make_svc(user_repo=user_repo, nomination_repo=nomination_repo)
    svc.period_repo.create.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()

    data = CotisationPeriodCreate(
        title="Don volontaire",
        cotisation_type=CotisationType.AUTRE,
        amount_expected=500,
        start_date=START,
        end_date=END,
    )
    await svc.create_period(data, uuid4())

    user_repo.list_paginated.assert_not_called()
    svc.payment_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_period_ordinaire_without_nomination_repo_skips_silently():
    """Si aucun nomination_repo n'est injecte (retro-compatibilite), pas de crash."""
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL, amount_expected=500)
    period_repo = MagicMock()
    period_repo.create = AsyncMock(return_value=period)
    payment_repo = MagicMock()
    payment_repo.get_period_stats = AsyncMock(return_value=_period_stats())
    payment_repo.create = AsyncMock()
    user_repo = MagicMock()
    user_repo.get = AsyncMock(return_value=None)

    svc = CotisationService(period_repo, payment_repo, user_repo)  # nomination_repo omis
    data = CotisationPeriodCreate(
        title="Cotisation Juin",
        cotisation_type=CotisationType.ORDINAIRE,
        period_type=PeriodType.MENSUEL,
        amount_expected=500,
        start_date=START,
        end_date=END,
    )
    result = await svc.create_period(data, uuid4())
    assert result.id == period.id
    payment_repo.create.assert_not_called()


# ── update_period ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_period_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_period(uuid4(), CotisationPeriodUpdate())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_period_success():
    period = _make_period(cotisation_type=CotisationType.SPECIALE)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.period_repo.update.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    data = CotisationPeriodUpdate(title="Nouveau Titre", is_active=False, amount_expected=6000)
    result = await svc.update_period(period.id, data)
    assert result.id == period.id


@pytest.mark.asyncio
async def test_update_period_ordinaire_wrong_amount_rejected():
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    data = CotisationPeriodUpdate(amount_expected=6000)
    with pytest.raises(Exception) as exc:
        await svc.update_period(period.id, data)
    assert exc.value.status_code == 400


# ── get_period ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_period_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_period(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_period_success():
    period = _make_period()
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats(0, 0, 0)
    result = await svc.get_period(period.id)
    assert result.id == period.id
    assert result.collection_rate == 0.0


@pytest.mark.asyncio
async def test_get_period_collection_rate():
    period = _make_period(amount_expected=5000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats(
        total_members=10, total_paid=7, total_amount_collected=35000
    )
    result = await svc.get_period(period.id)
    assert result.collection_rate == 70.0  # 7/10 * 100


# ── list_periods ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_periods_empty():
    svc = _make_svc()
    svc.period_repo.list_all.return_value = ([], 0)
    result = await svc.list_periods()
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_periods_with_items():
    period = _make_period()
    svc = _make_svc()
    svc.period_repo.list_all.return_value = ([period], 1)
    svc.payment_repo.get_period_stats.return_value = _period_stats()
    result = await svc.list_periods()
    assert result.total == 1
    assert len(result.items) == 1


# ── delete_period ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_period_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_period(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_period_success():
    period = _make_period()
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    await svc.delete_period(period.id)
    svc.period_repo.delete.assert_called_once_with(period.id)


# ── record_payment ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_payment_period_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    data = MemberCotisationCreate(period_id=uuid4(), user_id=uuid4(), amount_paid=5000)
    with pytest.raises(Exception) as exc:
        await svc.record_payment(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_record_payment_period_inactive():
    period = _make_period(is_active=False)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    data = MemberCotisationCreate(period_id=period.id, user_id=uuid4(), amount_paid=5000)
    with pytest.raises(Exception) as exc:
        await svc.record_payment(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_record_payment_user_not_found():
    period = _make_period(is_active=True)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = None
    data = MemberCotisationCreate(period_id=period.id, user_id=uuid4(), amount_paid=5000)
    with pytest.raises(Exception) as exc:
        await svc.record_payment(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_record_payment_new_full_payment():
    period = _make_period(amount_expected=5000)
    user = _make_user()
    payment = _make_payment(period_id=period.id, user_id=user.id, amount_paid=5000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_by_period_and_user.return_value = None
    svc.payment_repo.create.return_value = payment
    svc.payment_repo.enrich_cotisation.return_value = _enriched_payment(payment)
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=5000)
    result = await svc.record_payment(data, uuid4())
    assert result.id == payment.id
    svc.payment_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_record_payment_new_partial_payment():
    period = _make_period(amount_expected=5000)
    user = _make_user()
    payment = _make_payment(
        period_id=period.id, user_id=user.id, amount_paid=2500, status=CotisationStatus.PAYE_PARTIELLEMENT
    )
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_by_period_and_user.return_value = None
    svc.payment_repo.create.return_value = payment
    svc.payment_repo.enrich_cotisation.return_value = _enriched_payment(payment)
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=2500)
    result = await svc.record_payment(data, uuid4())
    assert result.id == payment.id


@pytest.mark.asyncio
async def test_record_payment_existing_updates():
    period = _make_period(amount_expected=5000)
    user = _make_user()
    existing = _make_payment(
        period_id=period.id, user_id=user.id, amount_paid=2500, status=CotisationStatus.PAYE_PARTIELLEMENT
    )
    updated = _make_payment(period_id=period.id, user_id=user.id, amount_paid=5000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_by_period_and_user.return_value = existing
    svc.payment_repo.update.return_value = updated
    svc.payment_repo.enrich_cotisation.return_value = _enriched_payment(updated)
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=2500)
    await svc.record_payment(data, uuid4())
    svc.payment_repo.update.assert_called_once()
    svc.payment_repo.create.assert_not_called()


# ── get_period_payments ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_period_payments_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_period_payments(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_period_payments_success():
    period = _make_period()
    payment = _make_payment(period_id=period.id)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.payment_repo.list_by_period.return_value = [payment]
    svc.payment_repo.enrich_cotisations.return_value = [_enriched_payment(payment)]
    result = await svc.get_period_payments(period.id)
    assert len(result) == 1


# ── get_user_payments ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_payments():
    user = _make_user()
    payment = _make_payment(user_id=user.id)
    svc = _make_svc()
    svc.payment_repo.list_by_user.return_value = [payment]
    svc.payment_repo.enrich_cotisations.return_value = [_enriched_payment(payment)]
    result = await svc.get_user_payments(user.id)
    assert len(result) == 1


# ── get_bilan ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_bilan_not_found():
    svc = _make_svc()
    svc.period_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_bilan(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_bilan_success():
    period = _make_period(amount_expected=5000)
    payment = _make_payment(period_id=period.id, amount_paid=5000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats(
        total_members=10, total_paid=8, total_amount_collected=40000
    )
    svc.payment_repo.list_by_period.return_value = [payment]
    svc.payment_repo.enrich_cotisations.return_value = [_enriched_payment(payment)]
    result = await svc.get_bilan(period.id)
    assert result.period.id == period.id
    assert result.total_collected == 40000
    assert result.taux_recouvrement == 80.0  # 8/10 * 100


@pytest.mark.asyncio
async def test_get_bilan_zero_members():
    period = _make_period(amount_expected=5000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.payment_repo.get_period_stats.return_value = _period_stats(0, 0, 0)
    svc.payment_repo.list_by_period.return_value = []
    svc.payment_repo.enrich_cotisations.return_value = []
    result = await svc.get_bilan(period.id)
    assert result.taux_recouvrement == 0.0


# ── record_payment : exclusivite mensuel/hebdomadaire (Art. 22) ────────────


@pytest.mark.asyncio
async def test_record_payment_rejects_cumul_mensuel_hebdo():
    """Un servant deja inscrit en hebdomadaire ne peut pas payer une periode mensuelle qui chevauche."""
    period = _make_period(cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.MENSUEL, amount_expected=500)
    user = _make_user()
    overlapping = _make_payment(user_id=user.id)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_overlapping_ordinaire_payment.return_value = overlapping
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=500)
    with pytest.raises(Exception) as exc:
        await svc.record_payment(data, uuid4())
    assert exc.value.status_code == 409
    svc.payment_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_record_payment_allows_when_no_overlap():
    period = _make_period(
        cotisation_type=CotisationType.ORDINAIRE, period_type=PeriodType.HEBDOMADAIRE, amount_expected=100
    )
    user = _make_user()
    payment = _make_payment(period_id=period.id, user_id=user.id, amount_paid=100)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_overlapping_ordinaire_payment.return_value = None
    svc.payment_repo.get_by_period_and_user.return_value = None
    svc.payment_repo.create.return_value = payment
    svc.payment_repo.enrich_cotisation.return_value = _enriched_payment(payment)
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=100)
    result = await svc.record_payment(data, uuid4())
    assert result.id == payment.id


@pytest.mark.asyncio
async def test_record_payment_speciale_ignores_exclusivity():
    """Les cotisations SPECIALE/AUBE ne sont pas soumises a la regle d'exclusivite."""
    period = _make_period(cotisation_type=CotisationType.SPECIALE, amount_expected=10000)
    user = _make_user()
    payment = _make_payment(period_id=period.id, user_id=user.id, amount_paid=10000)
    svc = _make_svc()
    svc.period_repo.get.return_value = period
    svc.user_repo.get.return_value = user
    svc.payment_repo.get_by_period_and_user.return_value = None
    svc.payment_repo.create.return_value = payment
    svc.payment_repo.enrich_cotisation.return_value = _enriched_payment(payment)
    data = MemberCotisationCreate(period_id=period.id, user_id=user.id, amount_paid=10000)
    result = await svc.record_payment(data, uuid4())
    assert result.id == payment.id
    svc.payment_repo.get_overlapping_ordinaire_payment.assert_not_called()


# ── check_payment_compliance (Art. 48, 50) ─────────────────────────────────


@pytest.mark.asyncio
async def test_check_payment_compliance_no_periods():
    svc = _make_svc()
    svc.period_repo.list_ordinaire_since.return_value = []
    result = await svc.check_payment_compliance(uuid4())
    assert result["needs_parent_convocation"] is False
    assert result["flagged_for_radiation"] is False


@pytest.mark.asyncio
async def test_check_payment_compliance_two_consecutive_missing():
    user_id = uuid4()
    p1 = _make_period(id=uuid4(), start_date=datetime(2026, 5, 1), end_date=datetime(2026, 5, 31))
    p2 = _make_period(id=uuid4(), start_date=datetime(2026, 4, 1), end_date=datetime(2026, 4, 30))
    svc = _make_svc()
    svc.period_repo.list_ordinaire_since.return_value = [p1, p2]
    svc.payment_repo.get_by_period_and_user.return_value = None
    result = await svc.check_payment_compliance(user_id)
    assert result["consecutive_missing_periods"] == 2
    assert result["needs_parent_convocation"] is True
    assert result["flagged_for_radiation"] is False


@pytest.mark.asyncio
async def test_check_payment_compliance_six_consecutive_missing_flags_radiation():
    user_id = uuid4()
    periods = [
        _make_period(id=uuid4(), start_date=datetime(2026, m, 1), end_date=datetime(2026, m, 28))
        for m in range(6, 0, -1)
    ]
    svc = _make_svc()
    svc.period_repo.list_ordinaire_since.return_value = periods
    svc.payment_repo.get_by_period_and_user.return_value = None
    result = await svc.check_payment_compliance(user_id)
    assert result["consecutive_missing_periods"] == 6
    assert result["flagged_for_radiation"] is True


@pytest.mark.asyncio
async def test_check_payment_compliance_paid_resets_streak():
    user_id = uuid4()
    p1 = _make_period(id=uuid4(), start_date=datetime(2026, 5, 1), end_date=datetime(2026, 5, 31))
    p2 = _make_period(id=uuid4(), start_date=datetime(2026, 4, 1), end_date=datetime(2026, 4, 30))
    paid = _make_payment(period_id=p1.id, user_id=user_id, status=CotisationStatus.PAYE)
    svc = _make_svc()
    svc.period_repo.list_ordinaire_since.return_value = [p1, p2]

    async def _get_by_period_and_user(period_id, uid):
        return paid if period_id == p1.id else None

    svc.payment_repo.get_by_period_and_user.side_effect = _get_by_period_and_user
    result = await svc.check_payment_compliance(user_id)
    assert result["consecutive_missing_periods"] == 1
    assert result["needs_parent_convocation"] is False
