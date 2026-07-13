# ServantAssist Backend — Guide Claude Code

## Vision
Plateforme digitale de gestion des servants d'autel de la **Basilique Marie Reine des Apôtres de Mvolyé** (Cameroun). Gère les présences, cotisations, affectations, discipline, formation, classement et communication pour ~300 servants.

## Stack technique
| Couche | Tech |
|--------|------|
| API | FastAPI 0.111 + Python 3.12 |
| ORM | SQLModel + asyncpg (PostgreSQL 16) |
| Cache | Redis 7 (sessions, rate-limit, token blacklist) |
| Async tasks | Celery 5.4 + Celery Beat + Flower |
| PDF | reportlab 4.1 |
| Email | aiosmtplib (SMTP async) |
| Chiffrement | AES-256-GCM (PII) + ECDH éphémère (payload) |
| Monitoring | Prometheus + Sentry |
| CI/CD | GitHub Actions |

## Architecture Clean Hexagonale
```
src/
  core/           → Entités, interfaces, exceptions, utils
  application/    → Use cases, services, DTOs, validators
  infrastructure/ → Repositories, services externes, Celery tasks
  presentation/   → Routers FastAPI, middlewares, dépendances, schemas
```

## Commandes essentielles
```bash
make dev           # Dev avec hot-reload (uvicorn)
make test          # pytest -v
make coverage      # pytest --cov + rapport HTML
make migrate       # alembic upgrade head
make rollback      # alembic downgrade -1
make lint          # ruff check + mypy
make docker-up     # Docker Compose dev
make flower        # Flower dashboard Celery (port 5555)
```

## Modules API (27 routers)
`analytics` `api_keys` `assignments` `attendance` `auth` `classement` `communication` `contributions` `cotisations` `dashboard` `discipline` `email` `events` `invitations` `materials` `nominations` `planning` `poste` `profiles` `reports` `sports_culture` `subgroups` `training` `treasury` `users` `websocket`

## Conformité Loi 2024/017 (Cameroun)
- **Chiffrement PII** : email, téléphone, dates → AES-256-GCM
- **Index HMAC** : lookup sans déchiffrement en clair
- **ECDH éphémère** : chiffrement payload POST/PUT/PATCH
- **Consentement** : tracé dans `data_consent_at` + `terms_accepted_at`
- **Droit à l'effacement (Art. 17)** : `POST /api/v1/users/me/erasure-request`
- **Portabilité (Art. 20)** : `GET /api/v1/users/me/data-export`

## Rôles utilisateurs
| Rôle | Accès |
|------|-------|
| `ADMIN` | Accès complet, gestion utilisateurs, finances |
| `AUMONIER` | Discipline, nominations, vue globale |
| `SERVANT` | Propre profil, présences, cotisations |
| `PARENT` | Suivi enfants, événements, annonces |

## Tâches Celery
| Tâche | Schedule | Fichier |
|-------|----------|---------|
| `send_event_reminders` | 8h00 quotidien | `scheduled.py` |
| `send_weekly_report` | lundi 7h00 | `scheduled.py` |
| `cleanup_notifications` | 2h00 quotidien | `scheduled.py` |
| `send_cotisation_reminders` | lundi 9h00 | `reminder_tasks.py` |
| `send_event_day_reminders` | 7h30 quotidien | `reminder_tasks.py` |
| `send_email_async` | on-demand | `email_tasks.py` |
| `export_user_data_pdf` | on-demand | `pdf_tasks.py` |

## Variables d'environnement critiques
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/servantassist
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=...          # JWT signing key (min 32 chars)
ENCRYPTION_KEY=...      # AES-256-GCM (32 bytes base64)
HMAC_KEY=...            # HMAC indexes (32 bytes base64)
SMTP_HOST=smtp.gmail.com
SMTP_USER=...
SMTP_PASSWORD=...
APP_ENV=development     # development | staging | production | testing
SENTRY_DSN=...
```
