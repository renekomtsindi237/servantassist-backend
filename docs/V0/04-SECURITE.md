# Modèle de Sécurité

> Mesures de sécurité implémentées à chaque couche de l'application.

---

## 1. Authentification JWT

### Structure des tokens

**Access Token** (durée : 30 min) :
```json
{
  "sub": "user@example.com",
  "role": "ADMIN",
  "exp": 1710000000
}
```

**Refresh Token** (durée : 7 jours) :
```json
{
  "sub": "user@example.com",
  "role": "ADMIN",
  "type": "refresh",
  "exp": 1710604800
}
```

**Reset Token** (durée : 15 min) :
```json
{
  "sub": "user@example.com",
  "type": "reset",
  "exp": 1710000900
}
```

### Sécurité JWT

| Mesure | Implémentation |
|---|---|
| Algorithme | HS256 avec clé secrète ≥ 32 caractères |
| Rôle obligatoire | `role` toujours présent dans le payload |
| Vérification cohérence | `auth_deps.py` compare rôle JWT ↔ rôle BDD |
| Tokens typés | Champ `type` pour différencier refresh/reset |
| Expiration stricte | Access: 30min, Refresh: 7j, Reset: 15min |
| Pas de stockage serveur | Stateless — validation par signature uniquement |

---

## 2. Contrôle d'Accès (RBAC)

### Matrice d'accès par rôle

| Ressource | ADMIN | AUMÔNIER | SERVANT | PARENT |
|---|---|---|---|---|
| **Auth** login email | ✅ | ✅ | ❌ | ❌ |
| **Auth** login phone | ❌ | ❌ | ✅ | ✅ |
| **Auth** register | ❌ | ❌ | ✅ | ✅ (code) |
| **Users** mon profil | ✅ | ✅ | ✅ | ✅ |
| **Users** modifier profil | ✅ | ✅ | ✅ | ✅ |
| **Users** lister tous | ✅ | ❌ | ❌ | ❌ |
| **Users** CRUD admin | ✅ | ❌ | ❌ | ❌ |
| **Admin** invitations | ✅ | ❌ | ❌ | ❌ |
| **Admin** créer rôles | ✅ | ❌ | ❌ | ❌ |
| **Events** lister/voir | ✅ | ✅ | ✅ | ✅ |
| **Events** créer/supprimer | ✅ | ❌ | ❌ | ❌ |
| **Assignments** créer | ✅ | ❌ | ❌ | ❌ |
| **Assignments** voir les miennes | ✅ | ✅ | ✅ | ✅ |
| **Assignments** voir par événement | ✅ | ✅ | ✅ | ✅ |

### Chaîne de dépendances d'autorisation

```
get_current_user         → Décode JWT, vérifie signature, récupère User en BDD
    ↓
get_current_active_user  → Vérifie user.is_active == True
    ↓
get_current_admin_user   → Vérifie user.role == ADMIN (403 sinon)
get_current_aumonier_user → Vérifie user.role == AUMÔNIER
get_current_parent_user   → Vérifie user.role == PARENT
get_current_servant_user  → Vérifie user.role == SERVANT
```

---

## 3. Protection Brute-Force

### Mécanisme progressif

```
Tentatives échouées → Verrouillage
─────────────────────────────────
5 échecs            → 1 minute
10 échecs           → 5 minutes
15 échecs           → 15 minutes
20+ échecs          → 30 minutes
```

### Détails d'implémentation

- **Stockage** : en mémoire (dictionnaire Python)
- **Clé** : identifiant normalisé (email lowercase ou téléphone)
- **Reset** : le compteur est remis à zéro après une connexion réussie
- **Nettoyage** : méthode `cleanup()` supprime les entrées > 1h sans activité
- **Production** : migrer vers Redis pour le stockage distribué

### Endpoints protégés

| Endpoint | Limite | Fenêtre |
|---|---|---|
| `/auth/login` | 5 req | 60s |
| `/auth/login/phone` | 5 req | 60s |
| `/auth/register` | 3 req | 60s |
| `/auth/forgot-password` | 3 req | 60s |
| `/auth/reset-password` | 3 req | 60s |
| Tous les autres | 60 req | 60s |

---

## 4. Hashage des Mots de Passe

| Propriété | Valeur |
|---|---|
| Algorithme | bcrypt |
| Librairie | passlib[bcrypt] 1.7.4 |
| Schéma | `bcrypt` |
| Auto-deprecated | Oui (`deprecated="auto"`) |
| Coût | 12 rounds (défaut bcrypt) |

### Politique de mot de passe

- Minimum **8 caractères**
- Au moins **1 majuscule** (`[A-Z]`)
- Au moins **1 minuscule** (`[a-z]`)
- Au moins **1 chiffre** (`\d`)
- Validé au niveau Pydantic (schema) + Pydantic `field_validator`

---

## 5. Headers de Sécurité HTTP (OWASP)

Appliqués par `SecurityHeadersMiddleware` sur **toutes** les réponses :

| Header | Valeur | Objectif |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | Force HTTPS (prod uniquement) |
| `X-Content-Type-Options` | `nosniff` | Empêche le MIME sniffing |
| `X-Frame-Options` | `DENY` | Empêche l'intégration en iframe |
| `X-XSS-Protection` | `1; mode=block` | Protection XSS navigateurs anciens |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; ...` | Politique de contenu |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Contrôle les informations referer |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Désactive APIs sensibles |
| `Cache-Control` | `no-store, no-cache, must-revalidate` | Endpoints `/auth/`, `/admin/` |
| `X-Powered-By` | `ServantAssist` | Masque la technologie serveur |

---

## 6. Protection contre les Injections

| Vecteur | Protection |
|---|---|
| **SQL Injection** | SQLModel/SQLAlchemy paramétrise toutes les requêtes |
| **XSS** | Pydantic valide les entrées, CSP bloque les scripts |
| **Email Injection** | `EmailStr` de Pydantic valide le format |
| **Format invalide** | Validation Pydantic renvoie `422`, pas d'erreur interne |

---

## 7. Anti-Énumération

| Technique | Implémentation |
|---|---|
| **Email** | `/forgot-password` retourne toujours 200 |
| **Login** | Message d'erreur identique pour email/password incorrect |
| **Register** | "Email already registered" (volontairement minimal) |

---

## 8. Sécurité Docker (Production)

```yaml
# docker-compose.prod.yml
backend:
  security_opt:
    - no-new-privileges:true    # Pas d'escalade de privilèges
  read_only: true               # Filesystem en lecture seule
  tmpfs:
    - /tmp:size=100M,noexec     # /tmp sans exécution
  cap_drop:
    - ALL                       # Supprime toutes les capabilities
  cap_add:
    - NET_BIND_SERVICE          # Seule la liaison réseau est permise
  deploy:
    resources:
      limits: { cpus: "2", memory: 1G }
      reservations: { cpus: "0.5", memory: 256M }

db:
  security_opt:
    - no-new-privileges:true
  cap_drop: [ALL]
  cap_add: [CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID]
  ports: []                     # Pas d'accès externe

redis:
  security_opt:
    - no-new-privileges:true
  cap_drop: [ALL]
  ports: []                     # Pas d'accès externe
  command: >
    redis-server
      --requirepass ${REDIS_PASSWORD}
      --rename-command FLUSHALL ""
      --rename-command CONFIG ""
      --rename-command DEBUG ""
```

---

## 9. Gestion des Erreurs en Production

```python
# En production : erreur opaque avec ID de traçabilité
{
    "detail": "An internal error occurred.",
    "error_id": "a1b2c3d4e5f6"
}

# En développement : détails complets
{
    "detail": "NoneType object has no attribute 'email'",
    "error_id": "a1b2c3d4e5f6",
    "type": "AttributeError"
}
```

- Chaque erreur 500 génère un `error_id` unique (UUID tronqué)
- Le log complet est enregistré côté serveur avec Loguru
- Le client reçoit uniquement l'`error_id` pour le support

---

## 10. Audit Trail

Le `LoggingMiddleware` produit des logs d'audit pour :

- Tous les accès aux endpoints `/api/v1/auth/*`
- Tous les accès aux endpoints `/api/v1/admin/*`
- Log enrichi : méthode, chemin, statut, durée, IP client, User-Agent

Format structuré JSON (production) :
```
AUDIT | POST /api/v1/auth/login | status=200 | ip=192.168.1.10 | ua=ServantAssist/1.0
```

