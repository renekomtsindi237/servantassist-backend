"""
Validateurs métier pour ServantAssist.

Conformité Loi 2024/017 (Cameroun) et contraintes opérationnelles :
- Téléphones : format international +237XXXXXXXXX
- Dates de naissance : plage acceptable 1940 → aujourd'hui-5ans
- Positions : enum des postes de l'organe exécutif
- Cotisations : plage XAF cohérente avec les montants habituels
- Périodes : format YYYY-MM pour cotisations et rapports
"""

import re
from datetime import date, datetime
from typing import Optional

# ── Téléphone ─────────────────────────────────────────────────────────────────

_PHONE_PATTERN = re.compile(r"^\+237[0-9]{9}$")


def validate_cameroon_phone(phone: str) -> str:
    """
    Valide et normalise un numéro de téléphone camerounais.

    Format accepté : +237XXXXXXXXX (9 chiffres après +237).
    Nettoie les espaces et tirets avant validation.

    Raises:
        ValueError: si le numéro ne respecte pas le format.
    """
    cleaned = re.sub(r"[\s\-\.]", "", phone.strip())
    if not _PHONE_PATTERN.match(cleaned):
        raise ValueError(
            f"Numéro de téléphone invalide : '{phone}'. " "Format attendu : +237XXXXXXXXX (9 chiffres après +237)."
        )
    return cleaned


# ── Date de naissance ─────────────────────────────────────────────────────────

_MIN_BIRTH_YEAR = 1940
_MIN_AGE_YEARS = 5


def validate_birthdate(date_value: Optional[str | date]) -> Optional[date]:
    """
    Valide une date de naissance.

    Contraintes :
    - Ne peut pas être dans le futur.
    - Ne peut pas être avant 1940.
    - L'age minimum est 5 ans (pas d'enfants trop jeunes).

    Args:
        date_value: chaîne ISO 8601 ou objet date, ou None.

    Returns:
        Objet date validé, ou None si date_value est None.

    Raises:
        ValueError: si la date ne respecte pas les contraintes.
    """
    if date_value is None:
        return None

    if isinstance(date_value, str):
        try:
            parsed = date.fromisoformat(date_value.split("T")[0])
        except ValueError:
            raise ValueError(f"Format de date invalide : '{date_value}'. Attendu : YYYY-MM-DD.")
    elif isinstance(date_value, datetime):
        parsed = date_value.date()
    else:
        parsed = date_value

    today = date.today()
    if parsed > today:
        raise ValueError("La date de naissance ne peut pas être dans le futur.")
    if parsed.year < _MIN_BIRTH_YEAR:
        raise ValueError(f"La date de naissance ne peut pas être avant {_MIN_BIRTH_YEAR}.")
    age = (today - parsed).days // 365
    if age < _MIN_AGE_YEARS:
        raise ValueError(f"L'âge minimum requis est {_MIN_AGE_YEARS} ans.")
    return parsed


# ── Position / Poste ──────────────────────────────────────────────────────────


# ── Montant de cotisation ─────────────────────────────────────────────────────

_MIN_COTISATION = 0.01
_MAX_COTISATION = 1_000_000.0


def validate_cotisation_amount(amount: float) -> float:
    """
    Valide un montant de cotisation en XAF.

    Plage : 0.01 XAF ≤ amount ≤ 1 000 000 XAF.

    Raises:
        ValueError: si le montant est hors plage.
    """
    if amount < _MIN_COTISATION:
        raise ValueError(f"Le montant de cotisation doit être supérieur à 0 XAF (reçu : {amount}).")
    if amount > _MAX_COTISATION:
        raise ValueError(
            f"Le montant de cotisation ne peut pas dépasser {_MAX_COTISATION:,.0f} XAF " f"(reçu : {amount:,.0f})."
        )
    return float(amount)


# ── Période ───────────────────────────────────────────────────────────────────

_PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate_contribution_period(period: str) -> str:
    """
    Valide une période de cotisation au format YYYY-MM.

    Contraintes :
    - Format strict YYYY-MM (ex. "2024-06").
    - Mois entre 01 et 12.
    - Année entre 2000 et 2100.

    Raises:
        ValueError: si le format ou la plage est invalide.
    """
    cleaned = period.strip()
    if not _PERIOD_PATTERN.match(cleaned):
        raise ValueError(f"Format de période invalide : '{period}'. Attendu : YYYY-MM (ex. 2024-06).")
    year = int(cleaned[:4])
    if not (2000 <= year <= 2100):
        raise ValueError(f"Année de période invalide : {year}. Plage acceptée : 2000–2100.")
    return cleaned
