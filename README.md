# ServantAssist Backend

FastAPI backend with Clean Architecture for ServantAssist platform.

## 🏗️ Architecture

- **Clean Architecture** (Hexagonal Architecture)
- **FastAPI** framework
- **PostgreSQL** database with Drizzle ORM
- **Redis** for caching
- **CloudFlare R2** for file storage

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment
cp .env .env.local  # adapter selon votre stratégie de secrets
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start server
uvicorn src.main:app --reload
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_user_service.py
```

## 🔐 CI/CD (J9-J10)

- CI bloquant sur: format/lint/typecheck + sécurité (`bandit`, `pip-audit`) + tests (`unit`, `security`, `use_cases`, `e2e`).
- Seuil de couverture progressif via variable `COVERAGE_MIN` (actuel: `65`).
- Job `Final Validation & RC` pour run complet avant release candidate.
- CD automatique vers serveur:
	- branche `dev`  -> déploiement serveur de développement
	- branche `main` -> déploiement serveur de production

### Secrets d'environnement (masquage)

Le pipeline ne log jamais le contenu des clés. Les fichiers d'environnement serveur sont passés en secret Base64:

```bash
base64 -w 0 .env.production > env.b64
```

Puis stocker le contenu dans:
- `DEV_ENV_FILE_B64` (développement)
- `PRODUCTION_ENV_FILE_B64` (production)

Le workflow:
- masque explicitement les secrets (`::add-mask::`),
- désactive l'echo shell (`set +x`) pendant les étapes sensibles,
- écrit le fichier runtime avec permissions strictes (`umask 177`).

Checklist RC/Go-live: `docs/RC_GO_LIVE_CHECKLIST.md`

## 📚 Documentation

- API Docs: http://localhost:8000/api/docs
- Architecture: [CLEAN_ARCHITECTURE.md](../docs/CLEAN_ARCHITECTURE.md)
- [📘 Guide Technique V0](./docs/TECHNICAL_V0.md)
- [🏛️ Spécifications Complètes (Platform)](../servantassist-platform/docs/V0_SPECS/)

## 🔗 Related Repositories

- [Platform](https://github.com/your-org/servantassist-platform)
- [Frontend Web](https://github.com/your-org/servantassist-web)
- [Frontend Mobile](https://github.com/your-org/servantassist-mobile)
