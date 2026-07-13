"""Unit tests for src/core/utils.py and src/core/entities/password_reset_code.py."""

import importlib
import sys
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import pytest

from src.core.utils import maybe_to_naive_utc, to_naive_utc, utc_now


# ─── utc_now ─────────────────────────────────────────────────────────────────


def test_utc_now_returns_datetime():
    result = utc_now()
    assert isinstance(result, datetime)


def test_utc_now_is_naive():
    """utc_now must return a naive datetime (no tzinfo)."""
    result = utc_now()
    assert result.tzinfo is None


def test_utc_now_roughly_now():
    """utc_now should be close to datetime.utcnow()."""
    before = datetime.utcnow()
    result = utc_now()
    after = datetime.utcnow()
    assert before <= result <= after


# ─── to_naive_utc ────────────────────────────────────────────────────────────


def test_to_naive_utc_with_naive_returns_same():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = to_naive_utc(naive)
    assert result == naive
    assert result.tzinfo is None


def test_to_naive_utc_with_aware_converts_to_utc():
    from datetime import timedelta

    # Create a UTC+2 aware datetime
    tz_plus2 = timezone(timedelta(hours=2))
    aware = datetime(2026, 1, 1, 14, 0, 0, tzinfo=tz_plus2)
    result = to_naive_utc(aware)
    # 14:00 UTC+2 == 12:00 UTC
    assert result == datetime(2026, 1, 1, 12, 0, 0)
    assert result.tzinfo is None


def test_to_naive_utc_utc_aware():
    aware_utc = datetime(2026, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = to_naive_utc(aware_utc)
    assert result == datetime(2026, 6, 15, 10, 30, 0)
    assert result.tzinfo is None


def test_to_naive_utc_negative_offset():
    from datetime import timedelta

    tz_minus5 = timezone(timedelta(hours=-5))
    aware = datetime(2026, 1, 1, 8, 0, 0, tzinfo=tz_minus5)
    result = to_naive_utc(aware)
    # 08:00 UTC-5 == 13:00 UTC
    assert result == datetime(2026, 1, 1, 13, 0, 0)
    assert result.tzinfo is None


# ─── maybe_to_naive_utc ──────────────────────────────────────────────────────


def test_maybe_to_naive_utc_none_returns_none():
    assert maybe_to_naive_utc(None) is None


def test_maybe_to_naive_utc_naive_passthrough():
    naive = datetime(2026, 3, 20, 8, 0, 0)
    result = maybe_to_naive_utc(naive)
    assert result == naive
    assert result.tzinfo is None


def test_maybe_to_naive_utc_aware():
    aware_utc = datetime(2026, 3, 20, 8, 0, 0, tzinfo=timezone.utc)
    result = maybe_to_naive_utc(aware_utc)
    assert result == datetime(2026, 3, 20, 8, 0, 0)
    assert result.tzinfo is None


# ─── PasswordResetCode entity ─────────────────────────────────────────────────


def test_password_reset_code_creation():
    """PasswordResetCode can be instantiated with required fields."""
    from datetime import timedelta

    from src.core.entities.password_reset_code import PasswordResetCode

    expires = datetime.utcnow() + timedelta(minutes=10)
    code = PasswordResetCode(
        email="test@example.com",
        code="123456",
        expires_at=expires,
    )
    assert isinstance(code.id, UUID)
    assert code.email == "test@example.com"
    assert code.code == "123456"
    assert code.expires_at == expires
    assert code.used is False
    assert isinstance(code.created_at, datetime)


def test_password_reset_code_used_flag():
    """PasswordResetCode used field defaults to False and can be set to True."""
    from datetime import timedelta

    from src.core.entities.password_reset_code import PasswordResetCode

    expires = datetime.utcnow() + timedelta(minutes=5)
    code = PasswordResetCode(
        email="another@example.com",
        code="654321",
        expires_at=expires,
        used=True,
    )
    assert code.used is True


def test_password_reset_code_unique_ids():
    """Each PasswordResetCode gets a unique UUID."""
    from datetime import timedelta

    from src.core.entities.password_reset_code import PasswordResetCode

    expires = datetime.utcnow() + timedelta(minutes=5)
    c1 = PasswordResetCode(email="a@b.com", code="111111", expires_at=expires)
    c2 = PasswordResetCode(email="a@b.com", code="222222", expires_at=expires)
    assert c1.id != c2.id


# ─── src/core/utils.py standalone file ──────────────────────────────────────
# Note: src/core/utils.py is shadowed by the src/core/utils/ package.
# We load it directly via importlib to exercise its lines and register coverage.


def _load_standalone_utils():
    """Load src/core/utils.py as a standalone module bypassing the package."""
    import importlib.util
    import os

    utils_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "src", "core", "utils.py",
    )
    utils_path = os.path.abspath(utils_path)
    spec = importlib.util.spec_from_file_location("_sa_core_utils_standalone", utils_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_standalone_utils_utc_now():
    mod = _load_standalone_utils()
    result = mod.utc_now()
    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_standalone_utils_to_naive_utc_naive():
    mod = _load_standalone_utils()
    naive = datetime(2026, 1, 1, 8, 0, 0)
    result = mod.to_naive_utc(naive)
    assert result == naive
    assert result.tzinfo is None


def test_standalone_utils_to_naive_utc_aware():
    from datetime import timedelta

    mod = _load_standalone_utils()
    tz_plus2 = timezone(timedelta(hours=2))
    aware = datetime(2026, 1, 1, 14, 0, 0, tzinfo=tz_plus2)
    result = mod.to_naive_utc(aware)
    assert result == datetime(2026, 1, 1, 12, 0, 0)
    assert result.tzinfo is None


def test_standalone_utils_maybe_to_naive_utc_none():
    mod = _load_standalone_utils()
    assert mod.maybe_to_naive_utc(None) is None


def test_standalone_utils_maybe_to_naive_utc_naive():
    mod = _load_standalone_utils()
    naive = datetime(2026, 5, 10, 9, 0, 0)
    result = mod.maybe_to_naive_utc(naive)
    assert result == naive


def test_standalone_utils_maybe_to_naive_utc_aware():
    mod = _load_standalone_utils()
    aware = datetime(2026, 5, 10, 9, 0, 0, tzinfo=timezone.utc)
    result = mod.maybe_to_naive_utc(aware)
    assert result == datetime(2026, 5, 10, 9, 0, 0)
    assert result.tzinfo is None
