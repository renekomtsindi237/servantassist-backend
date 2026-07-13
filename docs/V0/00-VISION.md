# ServantAssist — Vision Produit

> Application de gestion des enfants de chœur (servants d'autel) pour les paroisses.

---

## 1. Contexte

Dans les paroisses, la gestion des servants d'autel repose souvent sur des tableaux papier, des groupes WhatsApp informels et la mémoire de l'aumônier. Cela entraîne :

- Des oublis d'affectations lors des messes et célébrations
- Une communication inefficace entre l'aumônier, les servants et leurs parents
- L'absence de suivi des présences et de la progression des servants
- Une charge administrative importante pour l'aumônier

**ServantAssist** vise à centraliser et automatiser cette gestion dans une application mobile + API backend.

---

## 2. Objectif

Fournir un outil numérique permettant à l'aumônier et à un administrateur de :

1. **Gérer les servants** : inscription, profils, statuts
2. **Planifier les événements** : messes, répétitions, fêtes liturgiques
3. **Affecter les servants** : rôles liturgiques (cruciféraire, thurifer, etc.)
4. **Communiquer** : notifications aux servants et parents via WhatsApp/email
5. **Suivre les présences** : historique de participation

---

## 3. Utilisateurs et Rôles

| Rôle | Description | Méthode de connexion | Création |
|---|---|---|---|
| **ADMIN** | Administrateur principal. Gère tous les aspects. Unique. | Email + mot de passe | Script d'initialisation (`init_db.py`) |
| **AUMÔNIER** | Responsable spirituel des servants. Unique. | Email + mot de passe | Créé par l'ADMIN via `/admin/users/aumônier` |
| **SERVANT** | Enfant de chœur. Multiples. | Téléphone + mot de passe | Auto-inscription publique (`/register`) |
| **PARENT** | Parent d'un servant. Multiples. | Téléphone + mot de passe | Auto-inscription avec code d'invitation |

### Contraintes d'unicité

- **Un seul ADMIN** dans le système
- **Un seul AUMÔNIER** dans le système
- **Plusieurs SERVANT** et **PARENT** autorisés

---

## 4. Glossaire

| Terme | Définition |
|---|---|
| **Servant** | Enfant de chœur servant l'autel lors des cérémonies liturgiques |
| **Aumônier** | Prêtre ou diacre responsable de la formation et de l'encadrement des servants |
| **Assignment** | Affectation d'un servant à un rôle liturgique pour un événement donné |
| **Invitation Code** | Code unique généré par l'admin pour permettre l'inscription d'un parent |
| **Event** | Événement liturgique (messe, répétition, cérémonie) |
| **Role Name** | Rôle liturgique (Cruciféraire, Thuriféraire, Céroféraire, Naviculaire, etc.) |
| **JWT** | JSON Web Token utilisé pour l'authentification sans état (stateless) |
| **RBAC** | Role-Based Access Control — contrôle d'accès basé sur les rôles |

---

## 5. Périmètre MVP vs V0

### MVP (Minimum Viable Product) — en cours

Le MVP couvre les fonctionnalités essentielles pour une utilisation en paroisse :

| Module | Statut | Description |
|---|---|---|
| **Authentification** | ✅ Complet | Login, register, JWT, refresh, reset password, brute-force |
| **Gestion Utilisateurs** | ✅ Complet | CRUD, profil, pagination, activation/désactivation |
| **Événements** | 🔶 Partiel | CRUD basique (manque : update, récurrence, created_by) |
| **Affectations** | 🔶 Partiel | Création + listing (manque : accept/decline, présence) |
| **Communication** | ❌ Stub | Services email/WhatsApp existants, pas d'endpoints |

### V0 (Version 0 — release initiale)

Ajoute la complétude métier et la robustesse pour un déploiement réel :

- Module Événements complet (update, récurrence, créateur)
- Module Affectations complet (accept/decline, suivi présence)
- Module Communication (notifications, rappels)
- Gestion des groupes de servants
- Dashboard admin avec statistiques
- Application mobile (Android/iOS)

---

## 6. Stack Technique

| Composant | Technologie | Version |
|---|---|---|
| **Langage** | Python | 3.12 |
| **Framework API** | FastAPI | 0.109.0 |
| **ORM** | SQLModel (SQLAlchemy) | 0.0.14 |
| **Base de données** | PostgreSQL | 16 (Alpine) |
| **Cache / Rate Limit** | Redis | 7 (Alpine) |
| **Auth** | JWT (python-jose) | HS256 |
| **Hash MDP** | bcrypt (passlib) | 4.1.2 |
| **Stockage fichiers** | Cloudflare R2 (S3-compatible) | — |
| **WhatsApp** | Twilio | 8.10.0 |
| **Tests** | pytest + httpx + aiosqlite | — |
| **CI/CD** | GitHub Actions | — |
| **Conteneurisation** | Docker + Docker Compose | — |
| **Monitoring** | Prometheus (client) | 0.19.0 |
| **Logging** | Loguru (structuré JSON) | 0.7.2 |

---

## 7. Principes de Conception

1. **Clean Architecture** — Séparation stricte : Entités → Use Cases → Interface Adapters → Infrastructure
2. **RBAC** — Tout accès est contrôlé par rôle, vérifié dans le JWT et en base
3. **Security by Default** — Headers OWASP, rate limiting, brute-force protection, CSP
4. **API-First** — Le backend est une API REST consommée par le mobile
5. **Test-Driven Quality** — Suite de tests complète (unit, e2e, sécurité, use-cases, performance)
6. **Immutable Deployments** — Image Docker figée, pas de volume source en production

