# Changelog ServantAssist Backend

Toutes les modifications notables sont documentées ici.
Format : [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### Added
- **Validators métier** : `validate_cameroon_phone`, `validate_birthdate`, `validate_servant_position`, `validate_cotisation_amount`, `validate_contribution_period`
- **Conformité Loi 2024/017** : `POST /api/v1/users/me/erasure-request` (Art. 17) et `GET /api/v1/users/me/data-export` (Art. 20)
- **Tâches Celery** :
  - `email_tasks.py` : `send_email_async`, `send_welcome_email_async`, `send_assignment_email_async`, `send_reset_code_email_async`, `send_absence_notification_async`
  - `pdf_tasks.py` : `export_user_data_pdf`, `generate_attendance_report_pdf`, `generate_financial_report_pdf`
  - `reminder_tasks.py` : `send_cotisation_reminders` (lundi 9h), `send_event_day_reminders` (7h30)
- **Beat schedule** : 2 nouvelles tâches planifiées (cotisation reminders + event day reminders)
- **Documentation** : CLAUDE.md, TROUBLESHOOTING.md, CHANGELOG.md

---

## [0.1.0] — 2026-01

### Added
- Architecture Clean Hexagonale complète (core → application → infrastructure → presentation)
- 27 modules API avec 300+ endpoints
- 40 migrations Alembic
- Système d'authentification JWT (access + refresh tokens) avec liste noire Redis
- Chiffrement AES-256-GCM des données PII (email, téléphone, dates de naissance)
- Index HMAC pour lookups chiffrés sans déchiffrement
- Chiffrement ECDH éphémère des payloads POST/PUT/PATCH
- WebSocket temps réel (ConnectionManager)
- Rate limiting par Redis
- Celery Beat avec 3 tâches planifiées initiales (event reminders, weekly report, cleanup)
- Génération PDF avec reportlab
- Service email SMTP asynchrone avec templates HTML
- Upload photos de profil (Cloudflare R2)
- CI/CD GitHub Actions (lint + test + deploy)
- Docker Compose (dev/staging/production/simulation)
- Monitoring Prometheus + Sentry
