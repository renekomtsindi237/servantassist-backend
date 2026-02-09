"""
Protection contre les attaques par force brute.

Mecanisme :
- Apres N tentatives echouees sur un identifiant (email ou telephone),
  le compte est verrouille temporairement.
- Le verrouillage est progressif :
  * 5 echecs  -> verrouillage 1 min
  * 10 echecs -> verrouillage 5 min
  * 15 echecs -> verrouillage 15 min
  * 20+ echecs -> verrouillage 30 min
- Apres une connexion reussie, le compteur est reinitialise.

En production, utiliser Redis pour un stockage distribue.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class _LoginAttempt:
    """Suivi des tentatives de connexion pour un identifiant."""
    count: int = 0
    first_attempt: float = 0.0
    last_attempt: float = 0.0
    locked_until: float = 0.0


# Seuils progressifs : (nombre_echecs, duree_verrouillage_secondes)
_LOCKOUT_TIERS: list[Tuple[int, int]] = [
    (5, 60),       # 5 echecs  -> 1 min
    (10, 300),     # 10 echecs -> 5 min
    (15, 900),     # 15 echecs -> 15 min
    (20, 1800),    # 20 echecs -> 30 min
]


class BruteForceProtection:
    """Gestionnaire de protection brute-force en memoire."""

    def __init__(self):
        self._attempts: Dict[str, _LoginAttempt] = {}

    def _get_lockout_duration(self, count: int) -> int:
        """Retourne la duree de verrouillage en secondes selon le nombre d'echecs."""
        duration = 0
        for threshold, lock_seconds in _LOCKOUT_TIERS:
            if count >= threshold:
                duration = lock_seconds
        return duration

    def check_locked(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Verifie si un identifiant est verrouille.

        Retourne :
            (is_locked, seconds_remaining)
        """
        attempt = self._attempts.get(identifier)
        if not attempt:
            return False, None

        now = time.monotonic()
        if attempt.locked_until > now:
            remaining = int(attempt.locked_until - now) + 1
            return True, remaining

        return False, None

    def record_failure(self, identifier: str) -> Tuple[bool, int, Optional[int]]:
        """
        Enregistre un echec de connexion.

        Retourne :
            (is_now_locked, total_failures, lockout_seconds_if_locked)
        """
        now = time.monotonic()
        attempt = self._attempts.get(identifier)

        if not attempt:
            attempt = _LoginAttempt(
                count=1,
                first_attempt=now,
                last_attempt=now,
            )
            self._attempts[identifier] = attempt
        else:
            attempt.count += 1
            attempt.last_attempt = now

        # Verifier si on depasse un seuil
        lockout_duration = self._get_lockout_duration(attempt.count)
        if lockout_duration > 0:
            attempt.locked_until = now + lockout_duration
            return True, attempt.count, lockout_duration

        return False, attempt.count, None

    def record_success(self, identifier: str) -> None:
        """Reinitialise le compteur apres une connexion reussie."""
        self._attempts.pop(identifier, None)

    def get_remaining_attempts(self, identifier: str) -> int:
        """Retourne le nombre de tentatives restantes avant verrouillage."""
        attempt = self._attempts.get(identifier)
        if not attempt:
            return _LOCKOUT_TIERS[0][0]  # Premier seuil

        # Trouver le prochain seuil
        for threshold, _ in _LOCKOUT_TIERS:
            if attempt.count < threshold:
                return threshold - attempt.count
        return 0

    def cleanup(self, max_age: int = 3600) -> None:
        """Nettoie les entrees obsoletes (plus de max_age sans activite)."""
        now = time.monotonic()
        to_delete = [
            k for k, v in self._attempts.items()
            if now - v.last_attempt > max_age and v.locked_until < now
        ]
        for k in to_delete:
            del self._attempts[k]


# Singleton global
brute_force_guard = BruteForceProtection()

