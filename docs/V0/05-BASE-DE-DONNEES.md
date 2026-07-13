# Base de Données

> PostgreSQL 16 avec SQLModel (ORM) et Alembic (migrations).

---

## 1. Schéma Entité-Relation

```
┌───────────────────────┐       ┌───────────────────────┐
│        users          │       │        events         │
├───────────────────────┤       ├───────────────────────┤
│ id          UUID [PK] │       │ id          UUID [PK] │
│ email       str [UQ]  │       │ title       str       │
│ first_name  str       │       │ description str?      │
│ last_name   str       │       │ start_time  datetime  │
│ hashed_password str   │       │ end_time    datetime  │
│ role        enum      │       │ location    str       │
│ is_active   bool      │       │ event_type  enum      │
│ phone_number str? [IX]│       │ created_at  datetime  │
│ created_at  datetime  │       │ updated_at  datetime  │
│ updated_at  datetime  │       └───────┬───────────────┘
│ created_by  UUID? [FK]│───┐           │
│ invited_by  UUID? [FK]│───┤           │
└───────┬───────────────┘   │           │
        │                   │           │
        │ ┌─────────────────┘           │
        │ │                             │
        ▼ ▼                             │
┌───────────────────────┐               │
│    assignments        │               │
├───────────────────────┤               │
│ id          UUID [PK] │               │
│ event_id    UUID [FK] │───────────────┘
│ user_id     UUID [FK] │───── → users.id
│ role_name   str       │
│ status      enum      │
│ created_at  datetime  │
│ updated_at  datetime  │
└───────────────────────┘

┌───────────────────────────┐
│    invitation_codes       │
├───────────────────────────┤
│ id            UUID [PK]   │
│ code          str [UQ,IX] │
│ role          str          │
│ email         str?         │
│ phone_number  str?         │
│ status        enum         │
│ created_by    UUID [FK]    │──→ users.id
│ created_at    datetime     │
│ used_by       UUID? [FK]   │──→ users.id
│ used_at       datetime?    │
│ notes         str?         │
│ whatsapp_sent bool         │
└───────────────────────────┘
```

---

## 2. Entités détaillées

### Table `users`

```python
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID                  # PK, auto-généré uuid4
    email: str                # UNIQUE, INDEX — identifiant principal
    first_name: str
    last_name: str
    hashed_password: str      # bcrypt hash
    role: UserRole            # ADMIN | SERVANT | PARENT | AUMÔNIER
    is_active: bool           # défaut: True
    phone_number: str?        # INDEX — login pour PARENT/SERVANT
    created_at: datetime      # défaut: utcnow
    updated_at: datetime      # défaut: utcnow
    created_by: UUID?         # FK → users.id (admin qui a créé)
    invited_by: UUID?         # FK → users.id (pour PARENT)
```

**Enum `UserRole`** :
| Valeur | Description | Unicité |
|---|---|---|
| `ADMIN` | Administrateur | Un seul autorisé |
| `SERVANT` | Enfant de chœur | Multiple |
| `PARENT` | Parent de servant | Multiple |
| `AUMÔNIER` | Responsable spirituel | Un seul autorisé |

**Index** :
- `email` : UNIQUE + INDEX (login email)
- `phone_number` : INDEX (login téléphone)

---

### Table `events`

```python
class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: UUID                  # PK
    title: str
    description: str?
    start_time: datetime
    end_time: datetime
    location: str
    event_type: EventType     # MASS | REHEARSAL | OTHER
    created_at: datetime
    updated_at: datetime
```

**Enum `EventType`** :
| Valeur | Description |
|---|---|
| `MASS` | Messe (dimanche, semaine, solennité) |
| `REHEARSAL` | Répétition / Formation |
| `OTHER` | Autre (fête, retraite, pèlerinage) |

---

### Table `assignments`

```python
class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"

    id: UUID                  # PK
    event_id: UUID            # FK → events.id
    user_id: UUID             # FK → users.id
    role_name: str            # Rôle liturgique libre
    status: AssignmentStatus  # PENDING | ACCEPTED | DECLINED | PRESENT | ABSENT
    created_at: datetime
    updated_at: datetime
```

**Enum `AssignmentStatus`** :
| Valeur | Description | Transition |
|---|---|---|
| `PENDING` | En attente | → ACCEPTED, DECLINED |
| `ACCEPTED` | Le servant a accepté | → PRESENT, ABSENT |
| `DECLINED` | Le servant a décliné | (final) |
| `PRESENT` | Présent le jour J | (final) |
| `ABSENT` | Absent le jour J | (final) |

---

### Table `invitation_codes`

```python
class InvitationCode(SQLModel, table=True):
    __tablename__ = "invitation_codes"

    id: UUID                  # PK
    code: str                 # UNIQUE, INDEX — format "INV-{hex12}"
    role: str                 # "PARENT" ou "AUMÔNIER"
    email: str?               # Si limité à un email spécifique
    phone_number: str?        # Pour envoi WhatsApp
    status: InvitationStatus  # PENDING | ACCEPTED | REVOKED
    created_by: UUID          # FK → users.id (admin créateur)
    created_at: datetime
    used_by: UUID?            # FK → users.id (qui l'a utilisé)
    used_at: datetime?
    notes: str?               # Mémo libre
    whatsapp_sent: bool       # Si envoyé par WhatsApp
```

**Enum `InvitationStatus`** :
| Valeur | Description |
|---|---|
| `PENDING` | Pas encore utilisé |
| `ACCEPTED` | Utilisé pour une inscription |
| `REVOKED` | Annulé par l'admin |

---

## 3. Migrations (Alembic)

### Configuration

```
src/infrastructure/database/migrations/
├── env.py              # Configuration Alembic (async)
├── script.py.mako      # Template de migration
└── versions/           # Fichiers de migration versionnés
```

### Commandes

```bash
# Créer une nouvelle migration
alembic revision --autogenerate -m "description"

# Appliquer les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1

# Voir l'état
alembic current
alembic history
```

---

## 4. Connexion à la Base de Données

### Développement

```
postgresql+asyncpg://servantassist:servantassist_password@db:5432/servantassist_db
```

- Pool de connexions géré par SQLAlchemy
- Mode `echo=True` pour le debug SQL

### Tests

```
sqlite+aiosqlite:///:memory:
```

- Base en mémoire, recréée pour chaque test
- Tables créées via `SQLModel.metadata.create_all`
- Session isolée avec `expire_on_commit=False`

### Production

```
postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

- Variables d'environnement pour les credentials
- Pas d'accès externe à la DB (`ports: []` en production)
- Mode `echo=False`

---

## 5. Patterns de Repository

Tous les repositories implémentent l'interface générique :

```python
class IRepository(Generic[T]):
    async def get(self, id: UUID) -> Optional[T]
    async def list(self) -> List[T]
    async def create(self, entity: T) -> T
    async def update(self, id: UUID, entity: T) -> T
    async def delete(self, id: UUID) -> bool
```

Le `UserRepository` ajoute des méthodes spécifiques :

| Méthode | Description |
|---|---|
| `get_by_email(email)` | Recherche par email |
| `get_by_phone(phone)` | Recherche par téléphone |
| `list_paginated(role, is_active, search, page, page_size)` | Liste paginée avec filtres |
| `count_by_role(role)` | Comptage par rôle |
| `email_exists(email, exclude_id)` | Vérification unicité email |
| `phone_exists(phone, exclude_id)` | Vérification unicité téléphone |

---

## 6. Initialisation de la Base

Le script `scripts/init_db.py` crée l'administrateur initial :

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=SecurePass1 python scripts/init_db.py
```

- Les credentials sont **obligatoirement** passées via variables d'environnement
- Le script refuse de fonctionner sans ces variables
- Il vérifie si un admin existe déjà avant de le créer

