# DevOps — CI/CD, Docker, Déploiement

> Pipelines GitHub Actions + conteneurisation Docker multi-stage.

---

## 1. Pipeline CI (Intégration Continue)

**Fichier** : `.github/workflows/ci.yml`
**Déclencheur** : push/PR sur `main` et `develop`

### Jobs (7 étapes parallèles + séquentielles)

```
┌──────────┐    ┌─────────────────┐
│   Lint   │    │  Security Scan  │
│ (Black,  │    │  (Bandit,       │
│  isort,  │    │   pip-audit)    │
│  Flake8, │    └────────┬────────┘
│  MyPy)   │             │
└────┬─────┘             │
     │                   │
     ├────────┬──────────┤
     │        │          │
     ▼        ▼          ▼
┌─────────┐ ┌────────┐ ┌──────────────┐ ┌──────────────┐
│  Unit   │ │  E2E   │ │  Security    │ │  Use-Case    │
│  Tests  │ │  Tests │ │  Tests       │ │  Tests       │
└────┬────┘ └───┬────┘ └──────┬───────┘ └──────┬───────┘
     │          │             │                │
     ├──────────┤             │                │
     │          │             │                │
     ▼          ▼             │                │
┌──────────────────┐         │                │
│  Performance     │         │                │
│  Tests           │         │                │
└────────┬─────────┘         │                │
         │                   │                │
         ├───────────────────┼────────────────┤
         │                   │                │
         ▼                   ▼                ▼
    ┌──────────────────────────────────────────┐
    │           Coverage Report                │
    │  (pytest --cov --cov-fail-under=55)      │
    │  → Codecov + HTML artifact               │
    └──────────────────────────────────────────┘
```

### Détail des jobs

| Job | Dépend de | Outils | Seuil |
|---|---|---|---|
| **Lint** | — | Black, isort, Flake8 (max-line=120), MyPy | Bloquant (sauf MyPy) |
| **Security Scan** | — | Bandit (severity=medium), pip-audit | High = bloquant |
| **Unit Tests** | Lint | pytest `tests/unit/` + coverage XML | — |
| **E2E Tests** | Lint | pytest `tests/e2e/` + coverage XML | — |
| **Security Tests** | Lint + Scan | pytest `tests/security/` | — |
| **Use-Case Tests** | Lint | pytest `tests/use_cases/` | — |
| **Performance Tests** | Unit + E2E | pytest `tests/performance/` | — |
| **Coverage** | Unit + E2E + Security + UC | pytest full + Codecov | ≥ 55% |

### Variables d'environnement CI

```yaml
APP_ENV: testing
DATABASE_URL: "sqlite+aiosqlite:///:memory:"
JWT_SECRET_KEY: "ci-jwt-secret-key-minimum-32-chars-long-for-hs256!"
JWT_ALGORITHM: HS256
SECRET_KEY: "ci-app-secret-key-minimum-32-chars-long!"
CLOUDFLARE_R2_*: "ci-*"  # Valeurs factices
```

### Artefacts produits

| Artefact | Contenu |
|---|---|
| `bandit-report` | Rapport sécurité JSON |
| `unit-test-results` | coverage-unit.xml + junit-unit.xml |
| `e2e-test-results` | coverage-e2e.xml + junit-e2e.xml |
| `security-test-results` | junit-security.xml |
| `usecase-test-results` | junit-usecases.xml |
| `performance-test-results` | junit-performance.xml |
| `coverage-html` | Rapport HTML navigable |
| `full-test-results` | coverage.xml + junit-all.xml |

---

## 2. Pipeline CD (Déploiement Continu)

**Fichier** : `.github/workflows/cd.yml`
**Déclencheur** : CI réussi sur `main` + déclenchement manuel

### Jobs

```
CI réussi sur main
    │
    ▼
┌──────────────────┐
│  Build & Push    │  → Docker multi-stage → GHCR
│  (GHCR)          │  Tags: sha, branch, semver, latest
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Deploy Staging  │  → SSH → docker compose pull + up + alembic
│  + Health Check  │  → curl /health
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Deploy Prod     │  → Approbation manuelle requise
│  + Health Check  │  → SSH → docker compose pull + up + alembic
│  + Notify        │
└──────────────────┘
```

### Registry

- **Registry** : GitHub Container Registry (`ghcr.io`)
- **Image** : `ghcr.io/{org}/servantassist-backend`
- **Tags** : commit SHA, branche, version sémantique, `latest`
- **Cache** : GitHub Actions cache (`type=gha`)

### Déploiement

```bash
# Commandes exécutées sur le serveur cible
cd /opt/servantassist
docker compose pull backend
docker compose up -d backend
docker compose exec backend alembic upgrade head
```

### Environnements

| Environnement | Déclenchement | Approbation | URL |
|---|---|---|---|
| **Staging** | Automatique après build | Non | `$STAGING_URL` |
| **Production** | Après staging réussi | ✅ Manuelle | `$PRODUCTION_URL` |

---

## 3. Docker

### Images utilisées

| Service | Image | Version |
|---|---|---|
| Backend | Build custom (multi-stage) | Python 3.12-slim |
| PostgreSQL | `postgres:16-alpine` | 16 |
| Redis | `redis:7-alpine` | 7 |

### Docker Compose — Développement

```bash
# Démarrer tous les services
docker compose up

# Démarrer en arrière-plan
docker compose up -d

# Lancer les tests
docker compose --profile test up --abort-on-container-exit

# Voir les logs
docker compose logs -f backend
```

**Services** :
- `db` : PostgreSQL avec healthcheck `pg_isready`
- `redis` : Redis avec healthcheck `redis-cli ping`
- `backend` : FastAPI avec hot-reload (volume `.:/app`)
- `test` (profil test) : exécute `pytest` complet

### Docker Compose — Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Différences production** :
| Aspect | Développement | Production |
|---|---|---|
| Target Docker | `development` | `production` |
| Volumes source | `.:/app` (hot-reload) | Aucun (code figé dans l'image) |
| APP_ENV | `development` | `production` |
| APP_DEBUG | `True` | `False` |
| DB ports externes | `5432` exposé | Aucun (interne uniquement) |
| Redis ports | `6379` exposé | Aucun (interne uniquement) |
| Filesystem | read-write | **read-only** |
| Capabilities | Toutes | **Aucune** (sauf NET_BIND_SERVICE) |
| Limites ressources | Aucune | CPU: 2, RAM: 1G |
| Redis commands | Tous | FLUSHALL/CONFIG/DEBUG désactivés |

---

## 4. Outils de Qualité de Code

### Installés (`requirements-dev.txt`)

| Outil | Usage | Commande |
|---|---|---|
| **Black** | Formatage automatique | `black src/ tests/` |
| **isort** | Tri des imports | `isort src/ tests/` |
| **Flake8** | Linting PEP8 | `flake8 src/ tests/ --max-line-length=120` |
| **MyPy** | Vérification de types | `mypy src/ --ignore-missing-imports` |
| **Pylint** | Analyse statique avancée | `pylint src/` |
| **Bandit** | Sécurité Python | `bandit -r src/ --severity-level medium` |
| **pip-audit** | Vulnérabilités dépendances | `pip-audit --strict` |

### Configuration recommandée pour l'IDE

```bash
# Formatter au save
black --line-length=120 src/ tests/
isort --profile=black src/ tests/

# Vérifier avant commit
flake8 src/ tests/ --max-line-length=120
bandit -r src/ --severity-level high --confidence-level high
```

---

## 5. Monitoring (prévu)

| Composant | Outil | Statut |
|---|---|---|
| Métriques applicatives | Prometheus client | ✅ Dépendance installée |
| Export métriques | `/metrics` endpoint | ❌ À implémenter |
| Dashboards | Grafana | ❌ V1 |
| Alerting | Grafana Alerting | ❌ V1 |
| Logs centralisés | Loki / ELK | ❌ V1 |
| APM / Tracing | OpenTelemetry | ❌ V1 |

