"""
Service de stockage de fichiers (photos de profil, documents).

Modes de fonctionnement :
- **production** : Upload vers CloudFlare R2 via boto3 (S3-compatible)
  - Les photos de profil utilisent le bucket dédié ``profile``
    (configurable via ``CLOUDFLARE_R2_PROFILE_BUCKET``, défaut : ``profile``)
- **development/testing** : Stockage local dans /uploads/ avec URL relative

Configuration requise pour R2 (.env) :
  CLOUDFLARE_R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
  CLOUDFLARE_R2_ACCESS_KEY=<access-key>
  CLOUDFLARE_R2_SECRET_KEY=<secret-key>
  CLOUDFLARE_R2_BUCKET=servantassist
  CLOUDFLARE_R2_PROFILE_BUCKET=profile
  CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxx.r2.dev
"""
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from loguru import logger

from src.infrastructure.config.settings import get_settings

# Taille max de la photo de profil (5 Mo)
MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

# Dossier local pour le mode dev/test
LOCAL_UPLOAD_DIR = Path("uploads/profile_photos")


class StorageService:
    """Service d'upload/suppression de fichiers vers Cloudflare R2."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Propriétés de configuration ─────────────────────────────────────

    @property
    def _is_r2_configured(self) -> bool:
        """Verifie que les credentials R2 sont renseignes."""
        return bool(
            self._settings.CLOUDFLARE_R2_ACCESS_KEY
            and self._settings.CLOUDFLARE_R2_SECRET_KEY
            and self._settings.CLOUDFLARE_R2_ENDPOINT
            and self._settings.CLOUDFLARE_R2_BUCKET
            and not self._settings.CLOUDFLARE_R2_ENDPOINT.startswith("https://test")
        )

    @property
    def _is_testing(self) -> bool:
        return self._settings.APP_ENV == "testing"

    @property
    def _profile_bucket(self) -> str:
        """Retourne le nom du bucket dedie aux photos de profil."""
        return self._settings.CLOUDFLARE_R2_PROFILE_BUCKET

    # ── R2 (CloudFlare S3-compatible) ────────────────────────────────────

    def _get_r2_client(self):
        """Cree un client boto3 S3 pour CloudFlare R2."""
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self._settings.CLOUDFLARE_R2_ENDPOINT,
            aws_access_key_id=self._settings.CLOUDFLARE_R2_ACCESS_KEY,
            aws_secret_access_key=self._settings.CLOUDFLARE_R2_SECRET_KEY,
            region_name="auto",
        )

    async def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        Verifie que le bucket existe sur R2, le cree sinon.

        CloudFlare R2 supporte l'API S3 CreateBucket.
        """
        import asyncio

        def _sync_ensure():
            client = self._get_r2_client()
            try:
                client.head_bucket(Bucket=bucket_name)
                logger.debug("Bucket R2 existe | bucket={b}", b=bucket_name)
            except client.exceptions.ClientError:
                client.create_bucket(Bucket=bucket_name)
                logger.info("Bucket R2 cree | bucket={b}", b=bucket_name)

        await asyncio.to_thread(_sync_ensure)

    async def _upload_to_r2(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str,
        bucket: str,
    ) -> str:
        """Upload vers R2 dans le bucket specifie et retourne l'URL publique."""
        import asyncio

        await self._ensure_bucket_exists(bucket)

        def _sync_upload():
            client = self._get_r2_client()
            client.upload_fileobj(
                BytesIO(file_data),
                bucket,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000",
                },
            )

        await asyncio.to_thread(_sync_upload)
        public_url = (
            f"{self._settings.CLOUDFLARE_R2_PUBLIC_URL.rstrip('/')}"
            f"/{bucket}/{object_key}"
        )
        logger.info(
            "Fichier uploade vers R2 | bucket={bucket} | key={key} | url={url}",
            bucket=bucket,
            key=object_key,
            url=public_url,
        )
        return public_url

    async def _delete_from_r2(self, object_key: str, bucket: str) -> None:
        """Supprime un objet du bucket R2 specifie."""
        import asyncio

        def _sync_delete():
            client = self._get_r2_client()
            client.delete_object(Bucket=bucket, Key=object_key)

        await asyncio.to_thread(_sync_delete)
        logger.info(
            "Fichier supprime de R2 | bucket={bucket} | key={key}",
            bucket=bucket,
            key=object_key,
        )

    # ── Stockage local (dev/test) ────────────────────────────────────────

    async def _upload_local(
        self,
        file_data: bytes,
        object_key: str,
    ) -> str:
        """Sauvegarde localement et retourne l'URL relative."""
        LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filepath = LOCAL_UPLOAD_DIR / object_key.split("/")[-1]
        filepath.write_bytes(file_data)
        url = f"/uploads/profile_photos/{filepath.name}"
        logger.info("Fichier sauvegarde localement | path={path}", path=str(filepath))
        return url

    async def _delete_local(self, object_key: str) -> None:
        """Supprime un fichier local."""
        filename = object_key.split("/")[-1]
        filepath = LOCAL_UPLOAD_DIR / filename
        if filepath.exists():
            filepath.unlink()
            logger.info("Fichier local supprime | path={path}", path=str(filepath))

    # ── API publique ─────────────────────────────────────────────────────

    async def upload_profile_photo(
        self,
        user_id: str,
        file_data: bytes,
        content_type: str,
        filename: str,
    ) -> str:
        """
        Upload une photo de profil vers le bucket R2 **profile**.

        - **Bucket R2 utilisé** : ``CLOUDFLARE_R2_PROFILE_BUCKET`` (défaut : ``profile``)
        - **Object key** : ``{user_id}/{uuid}.{ext}``

        Validations :
        - Taille max : 5 Mo
        - Types autorises : JPEG, PNG, WebP

        Retourne l'URL publique de la photo.
        """
        # Validation taille
        if len(file_data) > MAX_PROFILE_PHOTO_SIZE:
            raise ValueError(
                f"La photo depasse la taille maximale autorisee "
                f"({MAX_PROFILE_PHOTO_SIZE // (1024 * 1024)} Mo)"
            )

        # Validation type
        if content_type not in ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(ALLOWED_CONTENT_TYPES.keys())
            raise ValueError(
                f"Type de fichier non autorise : {content_type}. "
                f"Types acceptes : {allowed}"
            )

        # Generer un nom unique
        ext = ALLOWED_CONTENT_TYPES[content_type]
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        object_key = f"{user_id}/{unique_name}"

        # Mode test : URL fictive avec le bucket profile
        if self._is_testing:
            url = f"https://test.r2.dev/{self._profile_bucket}/{object_key}"
            logger.info(
                "Upload simule (testing) | bucket={bucket} | key={key}",
                bucket=self._profile_bucket,
                key=object_key,
            )
            return url

        # Upload reel R2 (dans le bucket profile) ou local
        if self._is_r2_configured:
            return await self._upload_to_r2(
                file_data, object_key, content_type, bucket=self._profile_bucket
            )
        else:
            return await self._upload_local(file_data, object_key)

    async def delete_profile_photo(self, photo_url: str) -> None:
        """
        Supprime une photo de profil a partir de son URL.

        Detecte automatiquement si c'est une URL R2 ou locale.
        """
        if not photo_url:
            return

        # Mode test
        if self._is_testing:
            logger.info("Suppression simulee (testing) | url={url}", url=photo_url)
            return

        # URL R2 : extraire bucket + object_key
        r2_base = self._settings.CLOUDFLARE_R2_PUBLIC_URL.rstrip("/")
        bucket_prefix = f"{r2_base}/{self._profile_bucket}/"

        if self._is_r2_configured and photo_url.startswith(bucket_prefix):
            object_key = photo_url.replace(bucket_prefix, "")
            await self._delete_from_r2(object_key, bucket=self._profile_bucket)
        elif photo_url.startswith("/uploads/"):
            await self._delete_local(photo_url)
        else:
            logger.warning(
                "URL de photo non reconnue, suppression ignoree | url={url}",
                url=photo_url,
            )
