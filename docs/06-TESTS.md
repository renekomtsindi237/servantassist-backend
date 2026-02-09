# Stratégie de Tests

> 330 tests — 5 catégories — exécution complète en ~80 secondes.

---

## 1. Vue d'ensemble

| Catégorie | Répertoire | Marqueur pytest | Nombre | Objectif |
|---|---|---|---|---|
| **Unitaires** | `tests/unit/` | `@pytest.mark.unit` | ~60 | Tester les services et schemas en isolation |
| **E2E** | `tests/e2e/` | `@pytest.mark.e2e` | ~80 | Tester les endpoints HTTP complets |
| **Sécurité** | `tests/security/` | `@pytest.mark.security` | ~60 | RBAC, JWT, injections, headers |
| **Use-cases** | `tests/use_cases/` | `@pytest.mark.use_cases` | ~100 | Scénarios métier complets |
| **Performance** | `tests/performance/` | `@pytest.mark.performance` | ~30 | Charge, concurrence, latence |

---

## 2. Infrastructure de Test

### Base de données

- **Moteur** : SQLite async en mémoire (`sqlite+aiosqlite:///:memory:`)
- **Isolation** : base recréée pour chaque test (fixture `db_engine`)
- **Session** : `SQLModel.ext.asyncio.session.AsyncSession` avec `expire_on_commit=False`
- **Tables** : créées via `SQLModel.metadata.create_all`, détruites après chaque test

### Client HTTP

- **Framework** : `httpx.AsyncClient` avec `ASGITransport`
- **Application** : `FastAPI` minimal avec uniquement les routers nécessaires
- **Base URL** : `http://test` (pas de réseau réel)

### Fixtures partagées (`conftest.py`)

| Fixture | Scope | Description |
|---|---|---|
| `db_engine` | test | Moteur SQLite async en mémoire |
| `db_session` | test | Session DB liée au moteur de test |
| `app` | test | Application FastAPI avec session surchargée |
| `client` | test | Client HTTP async |
| `admin_user` | test | Utilisateur ADMIN en base |
| `aumonier_user` | test | Utilisateur AUMÔNIER en base |
| `servant_user` | test | Utilisateur SERVANT en base (+237600000001) |
| `parent_user` | test | Utilisateur PARENT en base (+237600000002) |
| `inactive_user` | test | Utilisateur SERVANT inactif |
| `valid_invitation` | test | Code d'invitation PENDING |
| `email_locked_invitation` | test | Invitation verrouillée à un email |
| `used_invitation` | test | Invitation déjà utilisée |

### Helpers

```python
VALID_PASSWORD = "TestPass1"  # 8+ chars, majuscule, minuscule, chiffre

def make_access_token(user) -> str:
    """Génère un access token pour un utilisateur de test."""

def make_auth_header(user) -> dict:
    """Retourne {'Authorization': 'Bearer <token>'}."""
```

---

## 3. Tests Unitaires (`tests/unit/`)

Testent les services et schemas **sans HTTP**, directement avec la session DB.

### `test_auth_service.py`
- Authentification email réussie/échouée
- Authentification téléphone réussie/échouée
- Inscription avec/sans invitation
- Création de tokens
- Refresh token valide/invalide
- Vérifications d'unicité (email, téléphone, rôles uniques)

### `test_user_service.py`
- **Update profil** : modification nom, téléphone, conflit unicité, PATCH partiel, suppression téléphone
- **Change password** : succès, mauvais ancien MDP, même MDP rejeté
- **List users** : tous, filtre rôle, filtre actif, recherche nom, recherche email, pagination
- **Admin update** : modification nom, email, conflit email, auto-désactivation interdite, user inexistant
- **Activate/Deactivate** : désactivation, déjà inactif, auto-désactivation, activation, déjà actif
- **Reset password** : réinitialisation forcée admin
- **Delete** : suppression, auto-suppression interdite, dernier admin interdit, user inexistant

### `test_schemas.py`
- Validation `UserCreate` (tous les champs)
- Validation mot de passe (trop court, sans majuscule, sans minuscule, sans chiffre)
- Validation téléphone (format invalide)
- Validation `UserCreateWithInvite`

### `test_security_utils.py`
- Hash + vérification bcrypt
- Création/décodage access token
- Création/décodage refresh token
- Création/décodage reset token

### `test_brute_force.py`
- Compteur d'échecs progressif
- Verrouillage aux seuils (5, 10, 15, 20)
- Reset après connexion réussie
- Nettoyage des entrées obsolètes

---

## 4. Tests E2E (`tests/e2e/`)

Testent le cycle HTTP complet (requête → middleware → endpoint → service → DB → réponse).

### `test_auth_endpoints.py`
- Login email : succès, identifiants incorrects, mauvais rôle
- Login téléphone : succès, identifiants incorrects
- Register : SERVANT, PARENT avec invitation, sans invitation rejetée
- Refresh : succès, token invalide
- Forgot/Reset password

### `test_admin_endpoints.py`
- Créer invitation PARENT
- Lister invitations
- Révoquer invitation
- Créer aumônier (vérifie unicité)
- Créer parent direct

### `test_user_endpoints.py`
- **GET /me** : servant, admin, non authentifié
- **PATCH /me** : prénom, téléphone, conflit, format invalide, PATCH partiel
- **PATCH /me/password** : succès, mauvais ancien, MDP faible
- **GET /** : admin OK, filtre rôle, recherche, pagination, servant 403
- **GET /{id}** : admin OK, inexistant 404
- **PATCH /{id}** : admin modifie nom, email
- **PATCH /{id}/deactivate** : succès, auto-désactivation 400
- **PATCH /{id}/activate** : succès
- **POST /{id}/reset-password** : succès
- **DELETE /{id}** : succès, auto-suppression 400, servant 403

---

## 5. Tests de Sécurité (`tests/security/`)

### `test_rbac.py`
- Chaque endpoint admin est inaccessible aux rôles SERVANT/PARENT
- Endpoints auth inaccessibles sans token

### `test_rbac_users.py`
- 7 endpoints admin-only testés avec SERVANT et PARENT → 403
- 4 endpoints self-service testés sans token → 401
- Isolation : SERVANT ne voit que son profil
- PARENT peut modifier son propre profil
- Utilisateur inactif → 400

### `test_jwt_security.py`
- Token expiré → 401
- Token avec signature invalide → 401
- Token avec rôle modifié → 401
- Token sans `sub` → 401
- Token sans `role` → 401
- SQL injection dans email → 401 (pas 500)
- XSS dans inscription → 422

### `test_security_hardening.py`
- Headers de sécurité OWASP présents
- Rate limiting fonctionnel
- Token algorigthm none rejeté

---

## 6. Tests Use-Cases (`tests/use_cases/`)

Scénarios métier complets simulant des workflows utilisateur réels.

### `test_uc_servant_registration.py`
1. Un servant s'inscrit, se connecte par téléphone, accède à son profil

### `test_uc_parent_invitation.py`
1. L'admin crée une invitation
2. Le parent s'inscrit avec le code
3. Le parent se connecte par téléphone

### `test_uc_admin_create_aumonier.py`
1. L'admin crée un aumônier
2. L'aumônier se connecte par email

### `test_uc_invitation_lifecycle.py`
1. Création → Utilisation → Vérification statut ACCEPTED
2. Création → Révocation → Inscription rejetée

### `test_uc_password_reset.py`
1. Forgot password → token généré → reset → login avec nouveau MDP

### `test_uc_token_lifecycle.py`
1. Login → access token → refresh → nouveaux tokens
2. Refresh invalide → rejeté
3. Access token comme refresh → rejeté
4. Token expiré → rejeté

### `test_uc_role_isolation.py`
1. SERVANT ne peut pas accéder aux endpoints admin
2. PARENT ne peut pas créer d'événement
3. ADMIN peut tout faire

### `test_uc_unique_roles.py`
1. Deux ADMIN → second rejeté
2. Deux AUMÔNIER → second rejeté
3. Multiples SERVANT → autorisé
4. Multiples PARENT → autorisé

### `test_uc_user_management.py`
1. Servant modifie son profil + change mot de passe
2. Admin filtre, désactive, réactive un utilisateur
3. Admin réinitialise un mot de passe
4. Suppression avec garde-fous (auto-suppression, dernier admin)

---

## 7. Tests de Performance (`tests/performance/`)

### `test_performance.py`
- **Login sequentiel** : temps de réponse moyen
- **Inscriptions concurrentes** : 10 utilisateurs simultanés
- **Token validation** : latence du décodage JWT
- **Listing utilisateurs** : réponse sous 500ms

---

## 8. Exécution

```bash
# Tous les tests
pytest

# Par catégorie
pytest -m unit
pytest -m e2e
pytest -m security
pytest -m use_cases
pytest -m performance

# Un fichier spécifique
pytest tests/unit/test_user_service.py -v

# Avec couverture
pytest --cov=src --cov-report=html --cov-report=term-missing

# Couverture minimale requise (CI)
pytest --cov=src --cov-fail-under=55
```

---

## 9. Configuration pytest

```ini
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto          # Toutes les fonctions async sont des tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short -p no:warnings
markers =
    unit: Unit tests (fast, no DB)
    e2e: End-to-end tests (full HTTP cycle)
    security: Security & RBAC tests
    performance: Performance & load tests
    use_cases: Use-case scenario tests (full business flows)
```

