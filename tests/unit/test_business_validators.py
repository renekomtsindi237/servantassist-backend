"""
Tests pour les validateurs métier (src/application/validators/business_validators.py).
"""

import pytest
from datetime import date, timedelta

from src.application.validators.business_validators import (
    validate_cameroon_phone,
    validate_birthdate,
    validate_cotisation_amount,
    validate_contribution_period,
)


# ── validate_cameroon_phone ────────────────────────────────────────────────────


class TestValidateCameroonPhone:
    def test_valid_standard(self):
        assert validate_cameroon_phone("+237612345678") == "+237612345678"

    def test_valid_with_spaces(self):
        assert validate_cameroon_phone("+237 612 345 678") == "+237612345678"

    def test_valid_with_dashes(self):
        assert validate_cameroon_phone("+237-612-345-678") == "+237612345678"

    def test_invalid_missing_plus(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("237612345678")

    def test_invalid_wrong_prefix(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("+33612345678")

    def test_invalid_too_short(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("+23761234567")  # 8 chiffres après +237

    def test_invalid_too_long(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("+2376123456789")  # 10 chiffres après +237

    def test_invalid_letters(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("+237ABCDEFGHI")

    def test_empty_string(self):
        with pytest.raises(ValueError, match="invalide"):
            validate_cameroon_phone("")

    def test_valid_starting_with_6(self):
        assert validate_cameroon_phone("+237699999999") == "+237699999999"

    def test_valid_starting_with_2(self):
        assert validate_cameroon_phone("+237222345678") == "+237222345678"


# ── validate_birthdate ─────────────────────────────────────────────────────────


class TestValidateBirthdate:
    def test_none_returns_none(self):
        assert validate_birthdate(None) is None

    def test_valid_date_string(self):
        result = validate_birthdate("1990-06-15")
        assert result == date(1990, 6, 15)

    def test_valid_date_object(self):
        d = date(1985, 3, 20)
        assert validate_birthdate(d) == d

    def test_valid_datetime_string_with_time(self):
        result = validate_birthdate("1990-06-15T10:30:00")
        assert result == date(1990, 6, 15)

    def test_future_date_raises(self):
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValueError, match="futur"):
            validate_birthdate(future.isoformat())

    def test_before_1940_raises(self):
        with pytest.raises(ValueError, match="1940"):
            validate_birthdate("1939-12-31")

    def test_min_age_too_young_raises(self):
        too_young = date.today() - timedelta(days=365)  # ~1 year old
        with pytest.raises(ValueError, match="minimum"):
            validate_birthdate(too_young.isoformat())

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Format"):
            validate_birthdate("15-06-1990")

    def test_boundary_year_1940(self):
        result = validate_birthdate("1940-01-01")
        assert result == date(1940, 1, 1)

    def test_adult_valid(self):
        adult = date.today() - timedelta(days=365 * 20)
        result = validate_birthdate(adult.isoformat())
        assert result == adult


# ── validate_cotisation_amount ─────────────────────────────────────────────────


class TestValidateCotisationAmount:
    def test_valid_normal_amount(self):
        assert validate_cotisation_amount(5000.0) == 5000.0

    def test_valid_minimum(self):
        assert validate_cotisation_amount(0.01) == pytest.approx(0.01)

    def test_valid_maximum(self):
        assert validate_cotisation_amount(1_000_000.0) == 1_000_000.0

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="supérieur"):
            validate_cotisation_amount(0.0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="supérieur"):
            validate_cotisation_amount(-100.0)

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="dépasser"):
            validate_cotisation_amount(1_000_001.0)

    def test_returns_float(self):
        result = validate_cotisation_amount(5000)
        assert isinstance(result, float)


# ── validate_contribution_period ──────────────────────────────────────────────


class TestValidateContributionPeriod:
    def test_valid_period(self):
        assert validate_contribution_period("2024-06") == "2024-06"

    def test_valid_january(self):
        assert validate_contribution_period("2024-01") == "2024-01"

    def test_valid_december(self):
        assert validate_contribution_period("2024-12") == "2024-12"

    def test_strips_whitespace(self):
        assert validate_contribution_period("  2024-06  ") == "2024-06"

    def test_invalid_format_no_dash(self):
        with pytest.raises(ValueError, match="Format"):
            validate_contribution_period("202406")

    def test_invalid_format_wrong_separator(self):
        with pytest.raises(ValueError, match="Format"):
            validate_contribution_period("2024/06")

    def test_invalid_month_00(self):
        with pytest.raises(ValueError, match="Format"):
            validate_contribution_period("2024-00")

    def test_invalid_month_13(self):
        with pytest.raises(ValueError, match="Format"):
            validate_contribution_period("2024-13")

    def test_invalid_year_too_old(self):
        with pytest.raises(ValueError, match="Année"):
            validate_contribution_period("1999-06")

    def test_invalid_year_too_far(self):
        with pytest.raises(ValueError, match="Année"):
            validate_contribution_period("2101-06")

    def test_boundary_year_2000(self):
        assert validate_contribution_period("2000-01") == "2000-01"

    def test_boundary_year_2100(self):
        assert validate_contribution_period("2100-12") == "2100-12"
