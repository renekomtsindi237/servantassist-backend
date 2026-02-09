# Architecture Technique

> Clean Architecture appliquée avec FastAPI, SQLModel et PostgreSQL.

---

## 1. Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                     CLIENTS (Mobile, Web)                    │
└──────────────────┬───────────────────────────────────────────┘
                   │ HTTPS / REST
┌──────────────────▼───────────────────────────────────────────┐
│              PRESENTATION LAYER                              │
│  ┌─────────────┐ ┌────────────┐ ┌──────────────┐            │
│  │  Middleware  │ │  API v1    │ │  Schemas     │            │
│  │  (6 layers) │ │  Endpoints │ │  (Pydantic)  │            │
│  └─────────────┘ └─────┬──────┘ └──────────────┘            │
│                         │ Dependencies (auth_deps.py)        │
└─────────────────────────┼────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│              APPLICATION LAYER                               │
│  ┌─────────────────┐ ┌──────────────┐ ┌────────────────┐    │
│  │  AuthService    │ │ UserService  │ │ EventService   │    │
│  │  (auth + JWT)   │ │ (profil+admin│ │ (CRUD events)  │    │
│  └─────────────────┘ └──────────────┘ └────────────────┘    │
│  ┌───────────────────┐                                       │
│  │ AssignmentService │                                       │
│  └───────────────────┘                                       │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              CORE / DOMAIN LAYER                             │
│  ┌────────────┐  ┌────────────────────┐  ┌───────────────┐  │
│  │  Entities  │  │  Interfaces (ABC)  │  │  Exceptions   │  │
│  │  User      │  │  IRepository<T>    │  │  (custom)     │  │
│  │  Event     │  │                    │  └───────────────┘  │
│  │  Assignment│  └────────────────────┘                     │
│  │  Invitation│                                              │
│  └────────────┘                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│              INFRASTRUCTURE LAYER                            │
│  ┌────────────────┐ ┌───────────────┐ ┌───────────────────┐ │
│  │  Repositories  │ │  Security     │ │  External Services│ │
│  │  (SQLModel)    │ │  (JWT, bcrypt)│ │  (Email, WhatsApp)│ │
│  └────────────────┘ │  (brute-force)│ └───────────────────┘ │
│  ┌────────────────┐ └───────────────┘                       │
│  │  Database      │ ┌───────────────┐                       │
│  │  (session mgr) │ │  Config       │                       │
│  └────────────────┘ │  (Settings)   │                       │
│                     └───────────────┘                       │
└──────────────────────────┬───────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   PostgreSQL 16       Redis 7         Cloudflare R2
```

---

## 2. Arborescence du projet

```
servantassist-backend/
├── src/
│   ├── main.py                          # Point d'entree FastAPI
│   ├── core/                            # DOMAINE (aucune dependance externe)
│   │   ├── entities/
│   │   │   ├── user.py                  # User, UserRole, UserBase
│   │   │   ├── event.py                 # Event, EventType
│   │   │   ├── assignment.py            # Assignment, AssignmentStatus
│   │   │   └── invitation.py            # InvitationCode, InvitationStatus
│   │   ├── interfaces/
│   │   │   ├── repository.py            # IRepository[T] (generique)
│   │   │   └── repositories/
│   │   │       └── user_repository.py   # Interface specifique User
│   │   └── exceptions/                  # Exceptions metier (a enrichir)
│   ├── application/                     # CAS D'UTILISATION (logique metier)
│   │   ├── services/
│   │   │   ├── auth_service.py          # Authentification, inscription, tokens
│   │   │   ├── user_service.py          # Profil, admin CRUD, pagination
│   │   │   ├── event_service.py         # Gestion des evenements
│   │   │   └── assignment_service.py    # Affectations servants ↔ evenements
│   │   ├── dtos/                        # Data Transfer Objects (a enrichir)
│   │   └── validators/                  # Validateurs metier (a enrichir)
│   ├── infrastructure/                  # ADAPTATEURS EXTERNES
│   │   ├── config/
│   │   │   └── settings.py              # Pydantic Settings (env vars)
│   │   ├── database/
│   │   │   ├── session.py               # DatabaseSessionManager (async)
│   │   │   └── migrations/              # Alembic
│   │   │       ├── env.py
│   │   │       └── versions/
│   │   ├── repositories/
│   │   │   ├── user_repository.py       # CRUD User + pagination + recherche
│   │   │   ├── event_repository.py      # CRUD Event + filtrage date
│   │   │   ├── assignment_repository.py # CRUD Assignment + list by user/event
│   │   │   └── invitation_repository.py # Gestion codes invitation
│   │   ├── security/
│   │   │   ├── utils.py                 # JWT, bcrypt, tokens
│   │   │   └── brute_force.py           # Protection progressive
│   │   └── services/
│   │       ├── email_service.py         # SMTP (mock en dev)
│   │       └── whatsapp_service.py      # Twilio WhatsApp
│   └── presentation/                    # INTERFACE HTTP
│       ├── api/v1/
│       │   ├── auth.py                  # /auth/* (login, register, refresh...)
│       │   ├── admin.py                 # /admin/* (invitations, creation roles)
│       │   ├── users.py                 # /users/* (profil, admin CRUD)
│       │   ├── activities.py            # /activities/* (evenements)
│       │   ├── assignments.py           # /assignments/* (affectations)
│       │   └── communication.py         # /communication/* (stub)
│       ├── dependencies/
│       │   └── auth_deps.py             # get_current_user, get_current_admin...
│       ├── middleware/
│       │   ├── error_handler.py         # Gestion erreurs 500 securisee
│       │   ├── logging_middleware.py     # Logging structurel + audit trail
│       │   ├── rate_limit.py            # Token bucket par IP
│       │   └── security_headers.py      # HSTS, CSP, X-Frame, etc.
│       └── schemas/
│           ├── auth.py                  # Token, UserCreate, UserLogin...
│           ├── user.py                  # UserProfileUpdate, Pagination...
│           ├── event.py                 # EventCreate, EventResponse
│           ├── assignment.py            # AssignmentCreate, AssignmentResponse
│           └── invitation.py            # InvitationCodeCreate/Response
├── tests/
│   ├── conftest.py                      # Fixtures globales (DB, client, users)
│   ├── unit/                            # Tests unitaires (services, schemas)
│   ├── e2e/                             # Tests bout-en-bout (HTTP complet)
│   ├── security/                        # Tests RBAC, JWT, injections
│   ├── use_cases/                       # Scenarios metier complets
│   └── performance/                     # Tests de charge
├── scripts/
│   └── init_db.py                       # Initialisation admin (env vars)
├── .github/workflows/
│   ├── ci.yml                           # Pipeline CI (7 jobs)
│   └── cd.yml                           # Pipeline CD (build → staging → prod)
├── docker-compose.yml                   # Dev + Test
├── docker-compose.prod.yml              # Override production (securise)
├── requirements.txt                     # Dependances production
├── requirements-dev.txt                 # Dependances developpement
└── pytest.ini                           # Configuration pytest
```

---

## 3. Pile de Middleware (ordre d'exécution)

Les middlewares sont empilés du plus externe au plus interne :

```
Requête entrante
    │
    ▼
┌─────────────────────────┐
│ 1. RateLimitMiddleware   │  Bloque avant traitement si quota dépassé
│    5 req/min auth        │  60 req/min global par IP
│    3 req/min register    │
├─────────────────────────┤
│ 2. LoggingMiddleware     │  Log structurel JSON + audit trail
│    - Durée, IP, UA       │  endpoints sensibles (/auth, /admin)
├─────────────────────────┤
│ 3. ErrorHandlerMiddleware│  Catch-all des exceptions non gérées
│    - Prod : erreur opaque│  - Dev : détails complets
│    - error_id pour trace │
├─────────────────────────┤
│ 4. SecurityHeaders       │  HSTS, CSP, X-Frame, X-XSS, Referrer,
│    (OWASP)               │  Permissions-Policy, Cache-Control
├─────────────────────────┤
│ 5. GZipMiddleware        │  Compression réponses > 1000 octets
├─────────────────────────┤
│ 6. CORSMiddleware        │  Origins configurables
│    - Credentials: true   │  GET, POST, PUT, PATCH, DELETE, OPTIONS
└─────────────────────────┘
    │
    ▼
  Endpoint FastAPI
```

---

## 4. Flux de Données (Exemple : Login)

```
Client POST /api/v1/auth/login
    │
    ▼
RateLimitMiddleware → vérifie quota IP
    │
    ▼
LoggingMiddleware → log début requête
    │
    ▼
auth.py::login_for_access_token()
    │
    ├─ 1. Vérif brute-force (brute_force_guard.check_locked)
    ├─ 2. Validation Pydantic (UserLogin)
    ├─ 3. AuthService.authenticate_user()
    │     ├─ UserRepository.get_by_email()
    │     ├─ Vérif rôle autorisé (ADMIN/AUMÔNIER pour email)
    │     ├─ SecurityUtils.verify_password()
    │     └─ Vérif is_active
    ├─ 4. AuthService.create_tokens()
    │     ├─ SecurityUtils.create_access_token(sub=email, role=role)
    │     └─ SecurityUtils.create_refresh_token(sub=email, role=role)
    └─ 5. Retour Token {access_token, refresh_token, token_type}
```

---

## 5. Pattern de Dépendances (Injection)

FastAPI utilise le système `Depends()` pour l'injection de dépendances :

```python
# Chaîne de dépendances pour un endpoint admin :
@router.get("/")
async def list_users(
    session: AsyncSession = Depends(get_db_session),       # DB
    current_user: User = Depends(get_current_admin_user),  # Auth + RBAC
):
    ...

# Résolution de la chaîne :
get_db_session          → SessionManager.session()
get_current_admin_user  → get_current_active_user → get_current_user
                          → jwt.decode() → UserRepository.get_by_email()
                          → vérif role == ADMIN
```

---

## 6. Gestion de la Session DB

```python
# Pattern async context manager
class DatabaseSessionManager:
    _engine: AsyncEngine
    _sessionmaker: async_sessionmaker

    async def session() -> AsyncGenerator[AsyncSession]:
        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

- **Développement** : `postgresql+asyncpg://` vers le container PostgreSQL
- **Tests** : `sqlite+aiosqlite:///:memory:` (base en mémoire, isolée par test)
- **Production** : PostgreSQL 16 avec pool de connexions

---

## 7. Variables d'Environnement Requises

| Variable | Obligatoire | Description | Exemple |
|---|---|---|---|
| `DATABASE_URL` | ✅ | URL PostgreSQL async | `postgresql+asyncpg://user:pass@host/db` |
| `JWT_SECRET_KEY` | ✅ | Clé secrète JWT (32+ chars) | `super-secret-key-min-32-characters` |
| `SECRET_KEY` | ✅ | Clé secrète application | `app-secret-key-min-32-characters` |
| `CLOUDFLARE_R2_*` | ✅ | Endpoint, Access/Secret Key, Bucket, URL | — |
| `APP_ENV` | ❌ | `development` / `testing` / `production` | `development` |
| `APP_DEBUG` | ❌ | Active le debug mode | `True` |
| `TWILIO_*` | ❌ | Credentials Twilio pour WhatsApp | — |
| `SMTP_*` | ❌ | Configuration serveur mail | — |
| `REDIS_URL` | ❌ | URL Redis | `redis://localhost:6379/0` |
| `ADMIN_EMAIL` | ⚠️ | Email admin (pour init_db.py) | `admin@example.com` |
| `ADMIN_PASSWORD` | ⚠️ | Mot de passe admin (pour init_db.py) | `SecurePass123` |

