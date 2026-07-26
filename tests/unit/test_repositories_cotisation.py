"""
Unit tests for cotisation repositories and invitation repository.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session() -> AsyncMock:
    return AsyncMock()


def _exec_result(first=None, all_=None, one=None):
    result = MagicMock()
    result.first = MagicMock(return_value=first)
    result.all = MagicMock(return_value=all_ if all_ is not None else [])
    result.one = MagicMock(return_value=one)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  CotisationPeriodRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_period(**kw):
    from src.core.entities.cotisation import CotisationPeriod, CotisationType

    return CotisationPeriod(
        id=kw.pop("id", uuid4()),
        title=kw.pop("title", "Période Test"),
        year=kw.pop("year", 2026),
        cotisation_type=kw.pop("cotisation_type", CotisationType.ORDINAIRE),
        amount_expected=kw.pop("amount_expected", 5000),
        is_active=kw.pop("is_active", True),
        created_by=kw.pop("created_by", uuid4()),
        **kw,
    )


def _make_member_cotisation(**kw):
    from src.core.entities.cotisation import CotisationStatus, MemberCotisation

    return MemberCotisation(
        id=kw.pop("id", uuid4()),
        period_id=kw.pop("period_id", uuid4()),
        user_id=kw.pop("user_id", uuid4()),
        amount_paid=kw.pop("amount_paid", 5000),
        status=kw.pop("status", CotisationStatus.PAYE),
        recorded_by=kw.pop("recorded_by", uuid4()),
        **kw,
    )


@pytest.mark.asyncio
async def test_cotisation_period_get_found():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    period = _make_period()
    session.exec = AsyncMock(return_value=_exec_result(first=period))

    result = await repo.get(period.id)
    assert result is period


@pytest.mark.asyncio
async def test_cotisation_period_get_not_found():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_cotisation_period_list_active():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    periods = [_make_period(), _make_period()]
    session.exec = AsyncMock(return_value=_exec_result(all_=periods))

    result = await repo.list_active()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_cotisation_period_list_all():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    periods = [_make_period()]
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=1),  # count
            _exec_result(all_=periods),  # items
        ]
    )

    result, total = await repo.list_all()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_cotisation_period_list_all_with_filter():
    from src.core.entities.cotisation import CotisationType
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=0),
            _exec_result(all_=[]),
        ]
    )

    result, total = await repo.list_all(cotisation_type=CotisationType.ORDINAIRE, is_active=True)
    assert result == []
    assert total == 0


@pytest.mark.asyncio
async def test_cotisation_period_create():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    period = _make_period()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(period)
    assert result is period
    session.add.assert_called_once_with(period)


@pytest.mark.asyncio
async def test_cotisation_period_update():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    period = _make_period()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(period)
    assert result is period


@pytest.mark.asyncio
async def test_cotisation_period_delete_found():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    period = _make_period()
    session.exec = AsyncMock(return_value=_exec_result(first=period))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(period.id)
    assert result is True
    session.delete.assert_called_once_with(period)


@pytest.mark.asyncio
async def test_cotisation_period_delete_not_found():
    from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository

    session = _mock_session()
    repo = CotisationPeriodRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False


# ─── MemberCotisationRepository ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_member_cotisation_get_found():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()
    session.exec = AsyncMock(return_value=_exec_result(first=cot))

    result = await repo.get(cot.id)
    assert result is cot


@pytest.mark.asyncio
async def test_member_cotisation_get_not_found():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_member_cotisation_get_by_period_and_user():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()
    session.exec = AsyncMock(return_value=_exec_result(first=cot))

    result = await repo.get_by_period_and_user(cot.period_id, cot.user_id)
    assert result is cot


@pytest.mark.asyncio
async def test_member_cotisation_list_by_period():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cots = [_make_member_cotisation()]
    session.exec = AsyncMock(return_value=_exec_result(all_=cots))

    result = await repo.list_by_period(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_member_cotisation_list_by_user():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cots = [_make_member_cotisation()]
    session.exec = AsyncMock(return_value=_exec_result(all_=cots))

    result = await repo.list_by_user(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_member_cotisation_get_period_stats():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)

    # Three exec calls: paid_count, total_collected, total_members
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=5),  # paid count
            _exec_result(one=25000),  # total collected
            _exec_result(one=10),  # total members
        ]
    )

    stats = await repo.get_period_stats(uuid4())
    assert stats["total_paid"] == 5
    assert stats["total_amount_collected"] == 25000.0
    assert stats["total_members"] == 10


@pytest.mark.asyncio
async def test_member_cotisation_create():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(cot)
    assert result is cot


@pytest.mark.asyncio
async def test_member_cotisation_update():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(cot)
    assert result is cot


@pytest.mark.asyncio
async def test_member_cotisation_delete_found():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()
    session.exec = AsyncMock(return_value=_exec_result(first=cot))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(cot.id)
    assert result is True


@pytest.mark.asyncio
async def test_member_cotisation_delete_not_found():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_member_cotisation_enrich_cotisation():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)

    cot = _make_member_cotisation()
    mock_user = MagicMock()
    mock_user.first_name = "Jean"
    mock_user.last_name = "Dupont"
    mock_period = MagicMock()
    mock_period.title = "Cotisation 2026"
    mock_period.amount_expected = 5000

    session.exec = AsyncMock(
        side_effect=[
            _exec_result(first=mock_user),
            _exec_result(first=mock_period),
        ]
    )

    with patch("src.infrastructure.repositories.cotisation_repository.decrypt_str_fields"):
        result = await repo.enrich_cotisation(cot)

    assert result["user_first_name"] == "Jean"
    assert result["period_title"] == "Cotisation 2026"


@pytest.mark.asyncio
async def test_member_cotisation_enrich_no_user():
    from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository

    session = _mock_session()
    repo = MemberCotisationRepository(session)
    cot = _make_member_cotisation()

    session.exec = AsyncMock(
        side_effect=[
            _exec_result(first=None),  # no user
            _exec_result(first=None),  # no period
        ]
    )

    result = await repo.enrich_cotisation(cot)
    assert result["user_first_name"] is None
    assert result["period_title"] is None


# ═══════════════════════════════════════════════════════════════════════════════
#  InvitationCodeRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_invitation(**kw):
    from src.core.entities.invitation import InvitationCode, InvitationStatus

    return InvitationCode(
        id=kw.pop("id", uuid4()),
        code=kw.pop("code", "INV-123456"),
        status=kw.pop("status", InvitationStatus.PENDING),
        created_by=kw.pop("created_by", uuid4()),
        expires_at=kw.pop("expires_at", None),
        **kw,
    )


def _make_enc_repo(session):
    from src.infrastructure.repositories.invitation_repository import InvitationCodeRepository

    repo = InvitationCodeRepository(session)
    # Patch encryption/decryption to be no-ops
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


@pytest.mark.asyncio
async def test_invitation_create():
    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.create(inv)
    assert result is inv
    session.add.assert_called_once_with(inv)


@pytest.mark.asyncio
async def test_invitation_get_by_code_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation()
    session.exec = AsyncMock(return_value=_exec_result(first=inv))

    result = await repo.get_by_code("INV-123456")
    assert result is inv
    repo._decrypt_model.assert_called_once_with(inv)


@pytest.mark.asyncio
async def test_invitation_get_by_code_not_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get_by_code("NOTEXIST")
    assert result is None


@pytest.mark.asyncio
async def test_invitation_get_by_id_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation()
    session.exec = AsyncMock(return_value=_exec_result(first=inv))

    result = await repo.get_by_id(inv.id)
    assert result is inv


@pytest.mark.asyncio
async def test_invitation_get_by_id_not_found():
    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_invitation_get_all_by_admin():
    session = _mock_session()
    repo = _make_enc_repo(session)
    invs = [_make_invitation(), _make_invitation()]
    session.exec = AsyncMock(return_value=_exec_result(all_=invs))

    result = await repo.get_all_by_admin(uuid4())
    assert len(result) == 2
    repo._decrypt_list.assert_called_once()


@pytest.mark.asyncio
async def test_invitation_is_valid_true():
    from src.core.entities.invitation import InvitationStatus

    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation(status=InvitationStatus.PENDING)
    session.exec = AsyncMock(return_value=_exec_result(first=inv))

    result = await repo.is_valid("INV-123456")
    assert result is True


@pytest.mark.asyncio
async def test_invitation_is_valid_false():
    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.is_valid("NOTEXIST")
    assert result is False


@pytest.mark.asyncio
async def test_invitation_revoke_not_found():
    from src.core.entities.invitation import InvitationStatus

    session = _mock_session()
    repo = _make_enc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.revoke(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_invitation_get_by_email():
    session = _mock_session()
    repo = _make_enc_repo(session)
    inv = _make_invitation()
    session.exec = AsyncMock(return_value=_exec_result(first=inv))

    mock_enc = MagicMock()
    mock_enc.hmac_index.return_value = "hmacvalue"

    with patch("src.infrastructure.repositories.invitation_repository.get_encryptor", return_value=mock_enc):
        result = await repo.get_by_email("test@example.com")

    assert result is inv
