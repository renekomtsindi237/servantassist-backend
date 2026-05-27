"""
Client Supabase centralisé — utilisé en staging et production.

Ce module expose deux clients :
  - supabase_admin  : service_role_key — opérations privilégiées (Storage, bypass RLS)
  - supabase_public : anon_key        — opérations publiques / côté utilisateur

En développement (APP_ENV=development), les clients sont None.
Les services qui consomment ce module doivent vérifier is_supabase_env
avant d'appeler ces clients.

Usage :
    from src.infrastructure.services.supabase_client import get_supabase_admin

    client = get_supabase_admin()
    # upload vers Supabase Storage
    client.storage.from_("profiles").upload(path, data)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from src.infrastructure.config.settings import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_supabase_admin():
    """
    Client Supabase avec service_role_key.
    Contourne les politiques RLS — à n'utiliser que côté serveur.
    Retourne None si APP_ENV=development.
    """
    if not settings.is_supabase_env:
        return None

    _assert_supabase_config()

    from supabase import create_client, Client  # import paresseux

    client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
    return client


@lru_cache(maxsize=1)
def get_supabase_public():
    """
    Client Supabase avec anon_key.
    Soumis aux politiques RLS — pour les opérations publiques.
    Retourne None si APP_ENV=development.
    """
    if not settings.is_supabase_env:
        return None

    _assert_supabase_config()

    from supabase import create_client, Client

    client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )
    return client


def _assert_supabase_config() -> None:
    missing = [
        name
        for name, val in [
            ("SUPABASE_URL", settings.SUPABASE_URL),
            ("SUPABASE_ANON_KEY", settings.SUPABASE_ANON_KEY),
            ("SUPABASE_SERVICE_ROLE_KEY", settings.SUPABASE_SERVICE_ROLE_KEY),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Variables Supabase manquantes : {', '.join(missing)}. "
            "Vérifiez votre fichier .env.staging / .env.production."
        )


# ── Helpers Storage ────────────────────────────────────────────────────────────


def upload_to_supabase_storage(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload un fichier vers Supabase Storage.
    Retourne l'URL publique du fichier.

    En développement, lève RuntimeError (doit être intercepté par l'appelant
    pour basculer sur Cloudflare R2).
    """
    client = get_supabase_admin()
    if client is None:
        raise RuntimeError(
            "Supabase Storage n'est pas disponible en développement. "
            "Utilisez Cloudflare R2."
        )

    client.storage.from_(bucket).upload(
        path,
        data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def delete_from_supabase_storage(bucket: str, path: str) -> None:
    """Supprime un fichier de Supabase Storage."""
    client = get_supabase_admin()
    if client is None:
        return
    client.storage.from_(bucket).remove([path])


def get_supabase_public_url(bucket: str, path: str) -> str:
    """Retourne l'URL publique d'un objet Supabase Storage."""
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
