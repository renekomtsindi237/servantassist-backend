"""
Middleware de déchiffrement de charge utile — Loi 2024/017 (Cameroun).

Appliqué sur POST / PUT / PATCH :
  - Si X-Client-Pubkey absent  → corps transmis tel quel (rétrocompatibilité dev).
  - Si X-Client-Pubkey présent → déchiffre le corps via PayloadEncryptor et
    réinjecte le JSON en clair avant de transmettre la requête au handler de route.

Retourne HTTP 400 si :
  - La clé publique éphémère est invalide.
  - Le corps chiffré est mal formé ou le tag GCM est invalide.
"""

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_ENCRYPTED_METHODS = {"POST", "PUT", "PATCH"}
_PUBKEY_HEADER = "x-client-pubkey"


class PayloadEncryptionMiddleware(BaseHTTPMiddleware):
    """Déchiffre les corps de requête chiffrés par les clients."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()

        if (
            not settings.PAYLOAD_ENCRYPTION_ENABLED
            or request.method not in _ENCRYPTED_METHODS
        ):
            return await call_next(request)

        client_pub_b64 = request.headers.get(_PUBKEY_HEADER)
        if not client_pub_b64:
            return await call_next(request)

        # Corps chiffré attendu
        try:
            encrypted_body = await request.body()
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"detail": "Impossible de lire le corps de la requête."},
            )

        if not encrypted_body:
            return JSONResponse(
                status_code=400,
                content={"detail": "Corps chiffré vide."},
            )

        # Déchiffrement
        try:
            from src.infrastructure.security.payload_encryption import get_payload_encryptor
            encryptor = get_payload_encryptor()
            plaintext = encryptor.decrypt_request(client_pub_b64, encrypted_body)
        except RuntimeError as exc:
            # Clé privée absente — signale une mauvaise configuration serveur
            logger.error("PayloadEncryption not configured: %s", exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "Chiffrement de charge utile non configuré côté serveur."},
            )
        except ValueError as exc:
            logger.warning("Payload decryption failed: %s", exc)
            return JSONResponse(
                status_code=400,
                content={"detail": f"Déchiffrement impossible : {exc}"},
            )

        # Réinjection du corps en clair dans la requête
        request._body = plaintext  # type: ignore[attr-defined]

        return await call_next(request)
