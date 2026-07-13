"""
Application settings and configuration
Using Pydantic Settings for environment variable management
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "ServantAssist"
    APP_ENV: str = "development"  # development | staging | production
    APP_DEBUG: bool = True
    APP_URL: str = "http://localhost:8000"

    # ── Database (development — PostgreSQL local) ──────────────────────
    DATABASE_URL: str = ""
    POSTGRES_USER: str = "servantassist"
    POSTGRES_PASSWORD: str = "servantassist_password"
    POSTGRES_DB: str = "servantassist_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ── Supabase (staging + production) ───────────────────────────────
    # Tableau de bord Supabase → Settings → API
    SUPABASE_URL: str = ""  # https://[project-ref].supabase.co
    SUPABASE_ANON_KEY: str = ""  # clé publique (safe côté client)
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # clé secrète (côté serveur uniquement)

    # Connexion directe à la base Supabase (utilisée par Alembic/migrations)
    # Dashboard → Settings → Database → Connection string → URI
    # Format : postgresql+asyncpg://postgres:[pwd]@db.[ref].supabase.co:5432/postgres
    SUPABASE_DB_DIRECT_URL: str = ""

    # Connection pooler Supabase — mode Transaction (port 6543)
    # Dashboard → Settings → Database → Connection pooling → Transaction
    # Format : postgresql+asyncpg://postgres.[ref]:[pwd]@aws-0-[region].pooler.supabase.com:6543/postgres
    SUPABASE_DB_POOLER_URL: str = ""

    @property
    def is_supabase_env(self) -> bool:
        """True pour staging et production (DB = Supabase)."""
        return self.APP_ENV in ("staging", "production")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cloudflare R2 (S3-compatible) — identifiants communs
    # Valeurs vides = R2 désactivé (fallback stockage local en dev/staging)
    CLOUDFLARE_R2_ENDPOINT: str = ""
    CLOUDFLARE_R2_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_SECRET_KEY: str = ""
    # Bucket par défaut : utilisé si un bucket spécialisé est vide (chaîne vide)
    CLOUDFLARE_R2_BUCKET: str = ""  # ex: servantassist
    # Buckets dédiés (noms tels qu’affichés dans le dashboard R2). Vide = réutiliser CLOUDFLARE_R2_BUCKET
    CLOUDFLARE_R2_BUCKET_IMAGES: str = ""  # images générales / médias hors profil
    CLOUDFLARE_R2_BUCKET_PROFILES: str = ""  # avatars, photos de profil
    CLOUDFLARE_R2_BUCKET_MATERIALS: str = ""  # photos matériel liturgique
    CLOUDFLARE_R2_BUCKET_TASKS: str = ""  # photos avant-après tâches entretien
    CLOUDFLARE_R2_BUCKET_REPORTS: str = ""  # pièces jointes rapports (secrétariat)
    CLOUDFLARE_R2_BUCKET_TRAINING: str = ""  # supports formation
    CLOUDFLARE_R2_BUCKET_DOCUMENTS: str = ""  # documents génériques (hors rapports/formation)
    CLOUDFLARE_R2_BUCKET_COMMUNICATION: str = ""  # PJ notifications, campagnes, médias comms
    CLOUDFLARE_R2_BUCKET_EXPORTS: str = ""  # exports CSV, fichiers temporaires export
    CLOUDFLARE_R2_BUCKET_BACKUPS: str = ""  # sauvegardes applicatives (optionnel)
    # URL publique par défaut (sans slash final). Domains ou pub-xxx.r2.dev
    CLOUDFLARE_R2_PUBLIC_URL: str = ""  # ex: https://pub-xxx.r2.dev
    # URL publique par usage (vide = réutiliser CLOUDFLARE_R2_PUBLIC_URL). Un domaine par bucket si besoin.
    CLOUDFLARE_R2_PUBLIC_URL_IMAGES: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_PROFILES: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_MATERIALS: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_TASKS: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_REPORTS: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_TRAINING: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_DOCUMENTS: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_COMMUNICATION: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_EXPORTS: str = ""
    CLOUDFLARE_R2_PUBLIC_URL_BACKUPS: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@servantassist.com"
    SMTP_FROM_NAME: str = "ServantAssist"
    SMTP_REPLY_TO: str = ""
    SMTP_USE_TLS: bool = True

    # Frontend (pour les liens dans les emails)
    FRONTEND_URL: str = "http://localhost:3000"

    # WhatsApp
    WHATSAPP_API_URL: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_FROM: str = ""  # Format: "whatsapp:+237xxxxxxxxx"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Security
    # Include 'testserver' so pytest TestClient requests pass host validation
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "testserver"]
    SECRET_KEY: str

    # Brute-force protection
    LOGIN_MAX_ATTEMPTS: int = 5  # Tentatives avant verrouillage
    LOGIN_LOCKOUT_SECONDS: int = 60  # Duree du premier palier de verrouillage

    # Rate limiting
    RATE_LIMIT_AUTH: int = 5  # Requêtes/min sur les endpoints auth
    RATE_LIMIT_GLOBAL: int = 60  # Requêtes/min global par IP
    # True en staging/prod (derrière Nginx-lb) — False en dev direct
    TRUST_PROXY_HEADERS: bool = False

    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "webp"]
    ALLOWED_DOCUMENT_EXTENSIONS: List[str] = ["pdf", "doc", "docx"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Sentry (optionnel — désactivé si None)
    SENTRY_DSN: str | None = None

    # ── Chiffrement des champs PII (Loi 2024/017 Cameroun) ────────────
    # Clé maître pour AES-256-GCM + index HMAC des données nominatives.
    # Générer avec : python -c "import secrets; print(secrets.token_urlsafe(48))"
    # Ne JAMAIS committer cette valeur. Elle reste dans le .env du développeur.
    FIELD_ENCRYPTION_KEY: str = ""

    # ── Chiffrement de charge utile (Loi 2024/017) ────────────────────
    # Clé privée EC P-256 (PEM PKCS#8, base64-encodé sur une ligne).
    # Générer avec : python scripts/generate_ec_keypair.py
    # La clé publique est distribuée aux clients via GET /api/v1/auth/server-pubkey.
    PAYLOAD_ENCRYPTION_PRIVATE_KEY: str = ""
    # Mettre à False en développement pour contourner le chiffrement de charge utile.
    PAYLOAD_ENCRYPTION_ENABLED: bool = True

    # ── Google Analytics Data API (service account) ────────────────────────
    # JSON du compte de service Google Cloud (sur une seule ligne, échappé).
    # Laisser vide pour désactiver l'intégration GA4.
    GOOGLE_SA_JSON: str = ""
    GA4_PROPERTY_ID: str = "539579421"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
