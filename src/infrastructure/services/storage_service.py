"""
Service de stockage de fichiers vers Cloudflare R2.

Organisation des objets dans le bucket R2 :

    images/
        profiles/    → photos de profil utilisateurs   (JPEG/PNG/WebP, max 5 Mo)
        materials/   → photos matériel liturgique       (JPEG/PNG/WebP, max 5 Mo)
        tasks/       → photos avant/après des tâches    (JPEG/PNG/WebP, max 5 Mo)
    documents/
        reports/     → pièces jointes aux rapports      (PDF/DOC/DOCX/images, max 10 Mo)
        training/    → matériels pédagogiques           (PDF/DOC/DOCX/images, max 10 Mo)
        general/     → documents génériques             (PDF/DOC/DOCX/images, max 10 Mo)
    communication/   → médias notifications, campagnes  (images/PDF, max 10 Mo)
    exports/         → fichiers CSV, XLS, exports temp  (max 50 Mo)
    backups/         → sauvegardes applicatives          (max 100 Mo)

Chaîne de fallback bucket (3 niveaux) :
    spécifique  (ex: CLOUDFLARE_R2_BUCKET_PROFILES)
    → catégorie (ex: CLOUDFLARE_R2_BUCKET_IMAGES)
    → défaut    (    CLOUDFLARE_R2_BUCKET)

Chaîne de fallback URL publique (3 niveaux) :
    spécifique  (ex: CLOUDFLARE_R2_PUBLIC_URL_PROFILES)
    → catégorie (ex: CLOUDFLARE_R2_PUBLIC_URL_IMAGES)
    → défaut    (    CLOUDFLARE_R2_PUBLIC_URL)

Quand tous les CLOUDFLARE_R2_BUCKET_* sont vides → un seul bucket,
isolation garantie par les préfixes de dossier.
Pour isoler par bucket → renseigner CLOUDFLARE_R2_BUCKET_IMAGES
et/ou CLOUDFLARE_R2_BUCKET_DOCUMENTS (les spécifiques héritent).
"""

import uuid
from io import BytesIO
from pathlib import Path

from loguru import logger

from src.infrastructure.config.settings import get_settings

# ── Préfixes d'objets par domaine ────────────────────────────────────────────

# Domaine Images
FOLDER_PROFILES = "images/profiles"
FOLDER_MATERIALS = "images/materials"
FOLDER_TASKS = "images/tasks"

# Domaine Documents
FOLDER_REPORTS = "documents/reports"
FOLDER_TRAINING = "documents/training"
FOLDER_DOCUMENTS = "documents/general"

# Domaines autonomes
FOLDER_COMMUNICATION = "communication"
FOLDER_EXPORTS = "exports"
FOLDER_BACKUPS = "backups"

# Lookup ordonné du plus spécifique au plus court — utilisé par _bucket_from_object_key
_ALL_FOLDERS = (
    FOLDER_PROFILES,
    FOLDER_MATERIALS,
    FOLDER_TASKS,
    FOLDER_REPORTS,
    FOLDER_TRAINING,
    FOLDER_DOCUMENTS,
    FOLDER_COMMUNICATION,
    FOLDER_EXPORTS,
    FOLDER_BACKUPS,
)

# ── Types MIME autorisés ─────────────────────────────────────────────────────

_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_DOCUMENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

_IMAGE_AND_DOCUMENT_TYPES: dict[str, str] = {**_IMAGE_TYPES, **_DOCUMENT_TYPES}

_EXPORT_TYPES: dict[str, str] = {
    "text/csv": "csv",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/zip": "zip",
}

# ── Limites de taille par domaine ────────────────────────────────────────────

_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 Mo — photos
_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024  # 10 Mo — documents / communication
_EXPORT_MAX_BYTES = 50 * 1024 * 1024  # 50 Mo — exports
_BACKUP_MAX_BYTES = 100 * 1024 * 1024  # 100 Mo — sauvegardes

# ── Stockage local (dev sans R2) ─────────────────────────────────────────────

_LOCAL_BASE = Path("uploads")


class StorageService:
    """
    Upload / suppression vers Cloudflare R2 (S3-compatible).

    Chaque domaine (images, documents, communication, exports, backups) est
    isolé par préfixe de dossier dans le bucket, ou par bucket dédié si les
    variables CLOUDFLARE_R2_BUCKET_* sont renseignées.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Propriétés ───────────────────────────────────────────────────────────

    @property
    def _is_r2_configured(self) -> bool:
        s = self._settings
        return bool(
            s.CLOUDFLARE_R2_ACCESS_KEY
            and s.CLOUDFLARE_R2_SECRET_KEY
            and s.CLOUDFLARE_R2_ENDPOINT
            and s.CLOUDFLARE_R2_BUCKET
            and not s.CLOUDFLARE_R2_ENDPOINT.startswith("https://test")
        )

    @property
    def _is_testing(self) -> bool:
        return self._settings.APP_ENV == "testing"

    def _default_bucket(self) -> str:
        return self._settings.CLOUDFLARE_R2_BUCKET

    # ── Résolution automatique du dossier depuis le type MIME ────────────────

    @staticmethod
    def _resolve_folder(context: str, content_type: str) -> str:
        """
        Route automatiquement vers le bon domaine selon le type MIME.

          image/*   → images/{context}
          CSV/XLS/… → exports/{context}
          autres    → documents/{context}

        ``context`` identifie l'entité métier (ex: "reports", "profiles").
        """
        if content_type in _IMAGE_TYPES:
            return f"images/{context}"
        if content_type in _EXPORT_TYPES:
            return f"exports/{context}"
        return f"documents/{context}"

    # ── Résolution bucket — chaîne de fallback 3 niveaux ─────────────────────

    def _bucket_for_folder(self, folder: str) -> str:
        """
        spécifique → catégorie → défaut

        Gère les dossiers nommés (FOLDER_*) ET les dossiers dynamiques
        créés par _resolve_folder (ex: "images/reports", "documents/tasks").
        """
        s = self._settings
        default = self._default_bucket()
        images = s.CLOUDFLARE_R2_BUCKET_IMAGES or default
        documents = s.CLOUDFLARE_R2_BUCKET_DOCUMENTS or default

        named = {
            FOLDER_PROFILES: s.CLOUDFLARE_R2_BUCKET_PROFILES or images,
            FOLDER_MATERIALS: s.CLOUDFLARE_R2_BUCKET_MATERIALS or images,
            FOLDER_TASKS: s.CLOUDFLARE_R2_BUCKET_TASKS or images,
            FOLDER_REPORTS: s.CLOUDFLARE_R2_BUCKET_REPORTS or documents,
            FOLDER_TRAINING: s.CLOUDFLARE_R2_BUCKET_TRAINING or documents,
            FOLDER_DOCUMENTS: documents,
            FOLDER_COMMUNICATION: s.CLOUDFLARE_R2_BUCKET_COMMUNICATION or default,
            FOLDER_EXPORTS: s.CLOUDFLARE_R2_BUCKET_EXPORTS or default,
            FOLDER_BACKUPS: s.CLOUDFLARE_R2_BUCKET_BACKUPS or default,
        }
        if folder in named:
            return named[folder]

        # Dossiers dynamiques — résolution par préfixe de domaine
        if folder.startswith("images/"):
            return images
        if folder.startswith("documents/"):
            return documents
        if folder.startswith("exports/") or folder == FOLDER_EXPORTS:
            return s.CLOUDFLARE_R2_BUCKET_EXPORTS or default
        if folder.startswith("communication/") or folder == FOLDER_COMMUNICATION:
            return s.CLOUDFLARE_R2_BUCKET_COMMUNICATION or default
        if folder.startswith("backups/") or folder == FOLDER_BACKUPS:
            return s.CLOUDFLARE_R2_BUCKET_BACKUPS or default
        return default

    # ── Résolution URL publique — chaîne de fallback 3 niveaux ───────────────

    def _public_base_for_folder(self, folder: str) -> str:
        """Même logique que _bucket_for_folder, appliquée aux URL publiques."""
        s = self._settings
        default = s.CLOUDFLARE_R2_PUBLIC_URL.rstrip("/")
        images = (s.CLOUDFLARE_R2_PUBLIC_URL_IMAGES or s.CLOUDFLARE_R2_PUBLIC_URL).rstrip("/")
        documents = (s.CLOUDFLARE_R2_PUBLIC_URL_DOCUMENTS or s.CLOUDFLARE_R2_PUBLIC_URL).rstrip("/")

        named = {
            FOLDER_PROFILES: s.CLOUDFLARE_R2_PUBLIC_URL_PROFILES or images,
            FOLDER_MATERIALS: s.CLOUDFLARE_R2_PUBLIC_URL_MATERIALS or images,
            FOLDER_TASKS: s.CLOUDFLARE_R2_PUBLIC_URL_TASKS or images,
            FOLDER_REPORTS: s.CLOUDFLARE_R2_PUBLIC_URL_REPORTS or documents,
            FOLDER_TRAINING: s.CLOUDFLARE_R2_PUBLIC_URL_TRAINING or documents,
            FOLDER_DOCUMENTS: documents,
            FOLDER_COMMUNICATION: s.CLOUDFLARE_R2_PUBLIC_URL_COMMUNICATION or default,
            FOLDER_EXPORTS: s.CLOUDFLARE_R2_PUBLIC_URL_EXPORTS or default,
            FOLDER_BACKUPS: s.CLOUDFLARE_R2_PUBLIC_URL_BACKUPS or default,
        }
        if folder in named:
            return (named[folder] or default).rstrip("/")

        if folder.startswith("images/"):
            return images
        if folder.startswith("documents/"):
            return documents
        if folder.startswith("exports/") or folder == FOLDER_EXPORTS:
            return (s.CLOUDFLARE_R2_PUBLIC_URL_EXPORTS or default).rstrip("/")
        if folder.startswith("communication/") or folder == FOLDER_COMMUNICATION:
            return (s.CLOUDFLARE_R2_PUBLIC_URL_COMMUNICATION or default).rstrip("/")
        if folder.startswith("backups/") or folder == FOLDER_BACKUPS:
            return (s.CLOUDFLARE_R2_PUBLIC_URL_BACKUPS or default).rstrip("/")
        return default

    # ── Résolution bucket depuis une clé d'objet (pour la suppression) ────────

    def _bucket_from_object_key(self, object_key: str) -> str:
        if not object_key:
            return self._default_bucket()
        for folder in _ALL_FOLDERS:
            if object_key.startswith(folder + "/"):
                return self._bucket_for_folder(folder)
        return self._default_bucket()

    def _all_public_bases(self) -> list[str]:
        """Toutes les URL publiques uniques, du plus long au plus court."""
        s = self._settings
        candidates = [
            s.CLOUDFLARE_R2_PUBLIC_URL,
            s.CLOUDFLARE_R2_PUBLIC_URL_IMAGES,
            s.CLOUDFLARE_R2_PUBLIC_URL_PROFILES,
            s.CLOUDFLARE_R2_PUBLIC_URL_MATERIALS,
            s.CLOUDFLARE_R2_PUBLIC_URL_TASKS,
            s.CLOUDFLARE_R2_PUBLIC_URL_REPORTS,
            s.CLOUDFLARE_R2_PUBLIC_URL_TRAINING,
            s.CLOUDFLARE_R2_PUBLIC_URL_DOCUMENTS,
            s.CLOUDFLARE_R2_PUBLIC_URL_COMMUNICATION,
            s.CLOUDFLARE_R2_PUBLIC_URL_EXPORTS,
            s.CLOUDFLARE_R2_PUBLIC_URL_BACKUPS,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for u in candidates:
            b = (u or "").strip().rstrip("/")
            if b and b not in seen:
                seen.add(b)
                out.append(b)
        out.sort(key=len, reverse=True)
        return out

    # ── Client boto3 ─────────────────────────────────────────────────────────

    def _get_r2_client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self._settings.CLOUDFLARE_R2_ENDPOINT,
            aws_access_key_id=self._settings.CLOUDFLARE_R2_ACCESS_KEY,
            aws_secret_access_key=self._settings.CLOUDFLARE_R2_SECRET_KEY,
            region_name="auto",
        )

    # ── Moteur R2 ─────────────────────────────────────────────────────────────

    async def _upload_to_r2(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str,
        *,
        bucket: str,
        public_base: str,
    ) -> str:
        import asyncio

        def _sync() -> None:
            self._get_r2_client().upload_fileobj(
                BytesIO(file_data),
                bucket,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000",
                },
            )

        await asyncio.to_thread(_sync)
        url = f"{public_base}/{object_key}"
        logger.info("Upload R2 | bucket={b} | key={k}", b=bucket, k=object_key)
        return url

    async def _delete_from_r2(self, object_key: str, bucket: str) -> None:
        import asyncio

        await asyncio.to_thread(lambda: self._get_r2_client().delete_object(Bucket=bucket, Key=object_key))
        logger.info("Suppression R2 | bucket={b} | key={k}", b=bucket, k=object_key)

    # ── Moteur local (dev sans R2) ────────────────────────────────────────────

    async def _upload_local(self, file_data: bytes, object_key: str) -> str:
        folder_dir = _LOCAL_BASE / Path(object_key).parent
        folder_dir.mkdir(parents=True, exist_ok=True)
        (folder_dir / Path(object_key).name).write_bytes(file_data)
        url = f"/uploads/{object_key}"
        logger.info("Upload local | path={p}", p=url)
        return url

    async def _delete_local(self, object_key: str) -> None:
        base = _LOCAL_BASE.resolve()
        filepath = (base / object_key).resolve()
        if not str(filepath).startswith(str(base)):
            logger.warning("Path traversal bloqué | key={k}", k=object_key)
            return
        if filepath.exists():
            filepath.unlink()
            logger.info("Suppression locale | path={p}", p=str(filepath))

    # ── Moteur générique ──────────────────────────────────────────────────────

    async def _upload(
        self,
        folder: str,
        owner_id: str,
        file_data: bytes,
        content_type: str,
        allowed_types: dict[str, str],
        max_bytes: int,
    ) -> str:
        if len(file_data) > max_bytes:
            raise ValueError(f"Fichier trop volumineux ({max_bytes // (1024 * 1024)} Mo max).")
        if content_type not in allowed_types:
            raise ValueError(f"Type non autorisé : {content_type}. " f"Acceptés : {', '.join(allowed_types)}.")
        safe_owner = "".join(c for c in str(owner_id) if c.isalnum() or c == "-")
        object_key = f"{folder}/{safe_owner}/{uuid.uuid4().hex}.{allowed_types[content_type]}"

        if self._is_testing:
            logger.info("Upload simulé (testing) | key={k}", k=object_key)
            return f"https://test.r2.dev/{object_key}"

        if self._is_r2_configured:
            return await self._upload_to_r2(
                file_data,
                object_key,
                content_type,
                bucket=self._bucket_for_folder(folder),
                public_base=self._public_base_for_folder(folder),
            )

        logger.warning("R2 non configuré — stockage local | key={k}", k=object_key)
        return await self._upload_local(file_data, object_key)

    async def _delete(self, file_url: str) -> None:
        if not file_url:
            return
        if self._is_testing:
            logger.info("Suppression simulée (testing) | url={u}", u=file_url)
            return
        for base in self._all_public_bases():
            if file_url.startswith(base + "/"):
                object_key = file_url[len(base) + 1 :]
                if self._is_r2_configured:
                    await self._delete_from_r2(object_key, self._bucket_from_object_key(object_key))
                else:
                    await self._delete_local(object_key)
                return
        if file_url.startswith("/uploads/"):
            await self._delete_local(file_url[len("/uploads/") :])
        else:
            logger.warning("URL non reconnue, suppression ignorée | url={u}", u=file_url)

    # ── API publique — Domaine Images ─────────────────────────────────────────

    async def upload_profile_photo(self, user_id: str, file_data: bytes, content_type: str) -> str:
        """Photo de profil → images/profiles/{user_id}/{uuid}.ext"""
        return await self._upload(
            FOLDER_PROFILES,
            user_id,
            file_data,
            content_type,
            _IMAGE_TYPES,
            _IMAGE_MAX_BYTES,
        )

    async def upload_material_photo(self, material_id: str, file_data: bytes, content_type: str) -> str:
        """Photo matériel → images/materials/{material_id}/{uuid}.ext"""
        return await self._upload(
            FOLDER_MATERIALS,
            material_id,
            file_data,
            content_type,
            _IMAGE_TYPES,
            _IMAGE_MAX_BYTES,
        )

    async def upload_task_photo(self, task_id: str, file_data: bytes, content_type: str) -> str:
        """Photo tâche (nettoyage/aubes avant-après) → images/tasks/{task_id}/{uuid}.ext"""
        return await self._upload(
            FOLDER_TASKS,
            task_id,
            file_data,
            content_type,
            _IMAGE_TYPES,
            _IMAGE_MAX_BYTES,
        )

    async def upload_sport_culture_photo(self, event_id: str, file_data: bytes, content_type: str) -> str:
        """Photo événement sport/culture → images/sport_culture/{event_id}/{uuid}.ext"""
        return await self._upload(
            "images/sport_culture",
            event_id,
            file_data,
            content_type,
            _IMAGE_TYPES,
            _IMAGE_MAX_BYTES,
        )

    # ── API publique — Domaine Documents ──────────────────────────────────────
    # Ces méthodes utilisent _resolve_folder : une image jointe à un rapport
    # va dans images/reports/, un PDF dans documents/reports/.

    async def upload_report_attachment(self, report_id: str, file_data: bytes, content_type: str) -> str:
        """PJ rapport — image → images/reports/, document → documents/reports/"""
        folder = self._resolve_folder("reports", content_type)
        return await self._upload(
            folder,
            report_id,
            file_data,
            content_type,
            _IMAGE_AND_DOCUMENT_TYPES,
            _DOCUMENT_MAX_BYTES,
        )

    async def upload_training_material(self, training_id: str, file_data: bytes, content_type: str) -> str:
        """Support formation — image → images/training/, document → documents/training/"""
        folder = self._resolve_folder("training", content_type)
        return await self._upload(
            folder,
            training_id,
            file_data,
            content_type,
            _IMAGE_AND_DOCUMENT_TYPES,
            _DOCUMENT_MAX_BYTES,
        )

    async def upload_document(self, owner_id: str, file_data: bytes, content_type: str) -> str:
        """Document générique — image → images/general/, document → documents/general/"""
        folder = self._resolve_folder("general", content_type)
        return await self._upload(
            folder,
            owner_id,
            file_data,
            content_type,
            _IMAGE_AND_DOCUMENT_TYPES,
            _DOCUMENT_MAX_BYTES,
        )

    # ── API publique — Domaine Communication ──────────────────────────────────

    async def upload_communication_media(self, campaign_id: str, file_data: bytes, content_type: str) -> str:
        """Média campagne — image → images/communication/, document → documents/communication/"""
        folder = self._resolve_folder("communication", content_type)
        return await self._upload(
            folder,
            campaign_id,
            file_data,
            content_type,
            _IMAGE_AND_DOCUMENT_TYPES,
            _DOCUMENT_MAX_BYTES,
        )

    # ── API publique — Exports & Sauvegardes ──────────────────────────────────

    async def upload_export(self, export_id: str, file_data: bytes, content_type: str) -> str:
        """Fichier export → exports/{export_id}/{uuid}.ext"""
        return await self._upload(
            FOLDER_EXPORTS,
            export_id,
            file_data,
            content_type,
            _EXPORT_TYPES,
            _EXPORT_MAX_BYTES,
        )

    async def upload_backup(self, backup_id: str, file_data: bytes, content_type: str) -> str:
        """Sauvegarde → backups/{backup_id}/{uuid}.ext"""
        return await self._upload(
            FOLDER_BACKUPS,
            backup_id,
            file_data,
            content_type,
            {**_EXPORT_TYPES, **_IMAGE_AND_DOCUMENT_TYPES},
            _BACKUP_MAX_BYTES,
        )

    # ── API publique — Upload générique automatique ───────────────────────────

    async def upload_file(self, context: str, owner_id: str, file_data: bytes, content_type: str) -> str:
        """
        Upload entièrement automatique — le domaine est déduit du type MIME.

          image/*   → images/{context}/{owner_id}/{uuid}.ext
          CSV/XLS/… → exports/{context}/{owner_id}/{uuid}.ext
          autres    → documents/{context}/{owner_id}/{uuid}.ext

        Exemple :
          await storage.upload_file("invoices", user_id, data, "application/pdf")
          → documents/invoices/{user_id}/{uuid}.pdf

          await storage.upload_file("invoices", user_id, data, "image/jpeg")
          → images/invoices/{user_id}/{uuid}.jpg
        """
        folder = self._resolve_folder(context, content_type)
        if content_type in _IMAGE_TYPES:
            allowed, max_bytes = _IMAGE_TYPES, _IMAGE_MAX_BYTES
        elif content_type in _EXPORT_TYPES:
            allowed, max_bytes = _EXPORT_TYPES, _EXPORT_MAX_BYTES
        else:
            allowed, max_bytes = _IMAGE_AND_DOCUMENT_TYPES, _DOCUMENT_MAX_BYTES
        return await self._upload(folder, owner_id, file_data, content_type, allowed, max_bytes)

    # ── Suppression générique ─────────────────────────────────────────────────

    async def delete_file(self, file_url: str) -> None:
        """Supprime n'importe quel fichier à partir de son URL publique."""
        await self._delete(file_url)
