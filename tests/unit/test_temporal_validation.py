"""
Tests unitaires pour la validation temporelle des modifications.

Ces tests démontrent que la validation fonctionne correctement pour :
- Les messes ordinaires (06h30, 08h30, 10h00, 11h30, 17h00)
- Les messes exceptionnelles (09h00, etc.)
- Différentes heures de tentative de modification
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.application.services.sunday_schedule_service import (
    is_within_mass_window,
    parse_mass_time,
)


class TestParseMassTime:
    """Tests pour le parsing des heures de messe."""

    def test_parse_standard_time(self):
        """Test parsing d'une heure standard."""
        hours, minutes = parse_mass_time("08h30")
        assert hours == 8
        assert minutes == 30

    def test_parse_early_morning(self):
        """Test parsing d'une heure matinale."""
        hours, minutes = parse_mass_time("06h30")
        assert hours == 6
        assert minutes == 30

    def test_parse_evening(self):
        """Test parsing d'une heure du soir."""
        hours, minutes = parse_mass_time("17h00")
        assert hours == 17
        assert minutes == 0

    def test_parse_exceptional_time(self):
        """Test parsing d'une heure exceptionnelle."""
        hours, minutes = parse_mass_time("09h00")
        assert hours == 9
        assert minutes == 0


class TestTemporalValidationOrdinaryMasses:
    """Tests pour les messes ordinaires."""

    def test_mass_0830_within_window(self):
        """
        Test : Messe de 08h30
        Fenêtre : 07h30 → 10h30
        """
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        mass_time = "08h30"

        # Avant la fenêtre (07h00) - REFUSÉ
        current = datetime(2026, 2, 16, 7, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Début de fenêtre (07h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 7, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Pendant la fenêtre (08h00) - AUTORISÉ
        current = datetime(2026, 2, 16, 8, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Heure de la messe (08h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 8, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après la messe (09h15) - AUTORISÉ
        current = datetime(2026, 2, 16, 9, 15, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Fin de fenêtre (10h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 10, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après la fenêtre (10h31) - REFUSÉ
        current = datetime(2026, 2, 16, 10, 31, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Bien après (11h00) - REFUSÉ
        current = datetime(2026, 2, 16, 11, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

    def test_mass_0630_within_window(self):
        """
        Test : Messe de 06h30
        Fenêtre : 05h30 → 08h30
        """
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        mass_time = "06h30"

        # Avant (05h00) - REFUSÉ
        current = datetime(2026, 2, 16, 5, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Début (05h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 5, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Pendant (06h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 6, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (07h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 7, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Fin (08h30) - AUTORISÉ
        current = datetime(2026, 2, 16, 8, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (08h31) - REFUSÉ
        current = datetime(2026, 2, 16, 8, 31, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

    def test_mass_1700_within_window(self):
        """
        Test : Messe de 17h00
        Fenêtre : 16h00 → 19h00
        """
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        mass_time = "17h00"

        # Avant (15h30) - REFUSÉ
        current = datetime(2026, 2, 16, 15, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Début (16h00) - AUTORISÉ
        current = datetime(2026, 2, 16, 16, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Pendant (17h00) - AUTORISÉ
        current = datetime(2026, 2, 16, 17, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (18h00) - AUTORISÉ
        current = datetime(2026, 2, 16, 18, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Fin (19h00) - AUTORISÉ
        current = datetime(2026, 2, 16, 19, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (19h01) - REFUSÉ
        current = datetime(2026, 2, 16, 19, 1, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False


class TestTemporalValidationExceptionalMasses:
    """Tests pour les messes exceptionnelles."""

    def test_exceptional_mass_0900_within_window(self):
        """
        Test : Messe exceptionnelle de 09h00
        Fenêtre : 08h00 → 11h00

        Démontre que la validation fonctionne EXACTEMENT de la même manière
        pour les messes exceptionnelles.
        """
        schedule_date = datetime(2026, 2, 23, tzinfo=timezone.utc)
        mass_time = "09h00"  # Heure exceptionnelle

        # Avant (07h30) - REFUSÉ
        current = datetime(2026, 2, 23, 7, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Début (08h00) - AUTORISÉ
        current = datetime(2026, 2, 23, 8, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Pendant (08h30) - AUTORISÉ
        current = datetime(2026, 2, 23, 8, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Heure de la messe (09h00) - AUTORISÉ
        current = datetime(2026, 2, 23, 9, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (10h00) - AUTORISÉ
        current = datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Fin (11h00) - AUTORISÉ
        current = datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (11h01) - REFUSÉ
        current = datetime(2026, 2, 23, 11, 1, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

    def test_exceptional_mass_1030_within_window(self):
        """
        Test : Messe solennelle exceptionnelle de 10h30
        Fenêtre : 09h30 → 12h30
        """
        schedule_date = datetime(2026, 3, 2, tzinfo=timezone.utc)
        mass_time = "10h30"  # Heure exceptionnelle pour une solennelle

        # Avant (09h00) - REFUSÉ
        current = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Début (09h30) - AUTORISÉ
        current = datetime(2026, 3, 2, 9, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Pendant (10h00) - AUTORISÉ
        current = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Heure de la messe (10h30) - AUTORISÉ
        current = datetime(2026, 3, 2, 10, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (11h30) - AUTORISÉ
        current = datetime(2026, 3, 2, 11, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Fin (12h30) - AUTORISÉ
        current = datetime(2026, 3, 2, 12, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # Après (12h31) - REFUSÉ
        current = datetime(2026, 3, 2, 12, 31, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False


class TestMultipleMassesSameDay:
    """Tests pour plusieurs messes le même jour."""

    def test_independent_windows(self):
        """
        Test : Plusieurs messes le même jour ont des fenêtres indépendantes.

        À 09h00 :
        - Messe 06h30 : fenêtre fermée (05h30-08h30)
        - Messe 08h30 : fenêtre ouverte (07h30-10h30)
        - Messe 10h00 : fenêtre ouverte (09h00-12h00)
        - Messe 11h30 : fenêtre pas encore ouverte (10h30-13h30)
        """
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        current = datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc)

        # Messe 06h30 - fenêtre fermée
        assert is_within_mass_window(schedule_date, "06h30", current) is False

        # Messe 08h30 - fenêtre ouverte
        assert is_within_mass_window(schedule_date, "08h30", current) is True

        # Messe 10h00 - fenêtre ouverte
        assert is_within_mass_window(schedule_date, "10h00", current) is True

        # Messe 11h30 - fenêtre pas encore ouverte
        assert is_within_mass_window(schedule_date, "11h30", current) is False

        # Messe 17h00 - fenêtre pas encore ouverte
        assert is_within_mass_window(schedule_date, "17h00", current) is False

    def test_overlapping_windows(self):
        """
        Test : Les fenêtres peuvent se chevaucher.

        À 10h00 :
        - Messe 08h30 : fenêtre encore ouverte (07h30-10h30)
        - Messe 10h00 : fenêtre ouverte (09h00-12h00)
        - Messe 11h30 : fenêtre pas encore ouverte (10h30-13h30)
        """
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        current = datetime(2026, 2, 16, 10, 0, tzinfo=timezone.utc)

        # Messe 08h30 - fenêtre encore ouverte
        assert is_within_mass_window(schedule_date, "08h30", current) is True

        # Messe 10h00 - fenêtre ouverte
        assert is_within_mass_window(schedule_date, "10h00", current) is True

        # Messe 11h30 - fenêtre pas encore ouverte
        assert is_within_mass_window(schedule_date, "11h30", current) is False


class TestEdgeCases:
    """Tests pour les cas limites."""

    def test_exact_window_boundaries(self):
        """Test des limites exactes de la fenêtre."""
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        mass_time = "08h30"

        # Exactement 1h avant (07h30:00) - AUTORISÉ
        current = datetime(2026, 2, 16, 7, 30, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # 1 seconde avant la fenêtre (07h29:59) - REFUSÉ
        current = datetime(2026, 2, 16, 7, 29, 59, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

        # Exactement 2h après le début (10h30:00) - AUTORISÉ
        current = datetime(2026, 2, 16, 10, 30, 0, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # 1 seconde après la fenêtre (10h30:01) - REFUSÉ
        current = datetime(2026, 2, 16, 10, 30, 1, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is False

    def test_midnight_crossing(self):
        """Test pour une messe très tôt le matin (fenêtre commence la veille)."""
        # Messe à 00h30 (minuit et demi)
        schedule_date = datetime(2026, 2, 16, tzinfo=timezone.utc)
        mass_time = "00h30"

        # 23h30 la veille - AUTORISÉ (1h avant)
        current = datetime(2026, 2, 15, 23, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

        # 02h30 le jour même - AUTORISÉ (2h après le début)
        current = datetime(2026, 2, 16, 2, 30, tzinfo=timezone.utc)
        assert is_within_mass_window(schedule_date, mass_time, current) is True

    def test_current_time_none_uses_now(self):
        """Test que current_time=None utilise l'heure actuelle."""
        schedule_date = datetime.now(timezone.utc)
        mass_time = "08h30"

        # Sans spécifier current_time, la fonction utilise datetime.now()
        # On ne peut pas tester le résultat exact, mais on vérifie qu'il n'y a pas d'erreur
        result = is_within_mass_window(schedule_date, mass_time)
        assert isinstance(result, bool)
