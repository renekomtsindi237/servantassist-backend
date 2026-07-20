"""
Vérification des jetons d'identité OAuth (Google) pour la connexion.

Vérifie directement la signature RS256 du jeton contre les clés publiques
(JWKS) de Google — aucune dépendance à un service d'auth tiers type
Supabase. `jwt.PyJWKClient` met en cache les clés récupérées (défaut : 5 min),
donc pas de round-trip réseau à chaque connexion.
"""

from typing import Optional

import jwt

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

_google_jwks_client: Optional[jwt.PyJWKClient] = None


class OAuthVerificationError(Exception):
    """Le jeton fourni n'a pas pu être vérifié (signature, audience, expiration...)."""


class OAuthIdentity:
    def __init__(self, email: Optional[str], email_verified: bool, subject: str):
        self.email = email
        self.email_verified = email_verified
        self.subject = subject


def _get_google_jwks_client() -> jwt.PyJWKClient:
    global _google_jwks_client
    if _google_jwks_client is None:
        _google_jwks_client = jwt.PyJWKClient(_GOOGLE_JWKS_URL)
    return _google_jwks_client


def verify_google_id_token(id_token: str, client_id: str) -> OAuthIdentity:
    """Vérifie un jeton d'identité Google (Google Identity Services)."""
    try:
        signing_key = _get_google_jwks_client().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
        )
    except jwt.PyJWTError as exc:
        raise OAuthVerificationError(f"Jeton Google invalide : {exc}") from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise OAuthVerificationError("Émetteur Google inattendu")

    return OAuthIdentity(
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        subject=str(claims["sub"]),
    )
