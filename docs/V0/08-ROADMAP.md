# Roadmap Complète

> Du MVP actuel à la V2 — planification par phases avec priorités et dépendances.

---

## Vue d'ensemble des phases

```
  MVP (actuel)          V0 (release)         V1 (enrichissement)       V2 (échelle)
  ─────────────         ────────────         ────────────────────      ──────────────
  Auth ✅               Events complet       Groupes de servants       Multi-paroisse
  Users ✅              Assignments complet  Planning automatique      API publique
  Events 🔶            Communication        Statistiques/Dashboard    PWA / Web app
  Assignments 🔶       Tests complets       Notifications push        Analytics
  Communication ❌      Mobile Android       Calendrier partagé        Marketplace
                        Migration Alembic    iOS                       IA suggestions
```

---

## Phase 1 : MVP (état actuel) ✅

### Module Authentification ✅
- [x] Login email (ADMIN, AUMÔNIER)
- [x] Login téléphone (PARENT, SERVANT)
- [x] Inscription avec filtrage de rôles
- [x] Système d'invitation pour PARENT
- [x] JWT avec rôle embarqué (access + refresh + reset tokens)
- [x] Protection brute-force progressive (4 paliers)
- [x] Rate limiting par IP et par endpoint
- [x] Headers de sécurité OWASP
- [x] Forgot/reset password
- [x] Création aumônier/admin par l'admin
- [x] 261 tests (unit, e2e, security, use-cases, performance)

### Module Utilisateurs ✅
- [x] Profil self-service (GET/PATCH /me)
- [x] Changement de mot de passe (ancien requis)
- [x] Liste paginée avec filtres (rôle, actif, recherche)
- [x] CRUD admin complet (update, activate, deactivate, delete)
- [x] Réinitialisation forcée du mot de passe par admin
- [x] Garde-fous (auto-suppression, dernier admin)
- [x] Unicité email et téléphone
- [x] 69 tests supplémentaires

### Infrastructure ✅
- [x] Clean Architecture (4 couches)
- [x] Docker Compose (dev + test + prod)
- [x] Pipeline CI (7 jobs GitHub Actions)
- [x] Pipeline CD (build → staging → production)
- [x] Durcissement Docker production
- [x] Logging structuré avec audit trail
- [x] Gestion d'erreurs sécurisée

---

## Phase 2 : V0 — Release Initiale 🎯

> Objectif : application utilisable en paroisse avec toutes les fonctionnalités de base.

### 2.1 Module Événements — Complétion ⏳

**Priorité : HAUTE** | **Effort : 2 sprints**

- [ ] `PATCH /activities/{id}` — Modifier un événement
- [ ] Ajout du champ `created_by` (UUID FK → users) dans l'entité Event
- [ ] Pagination des événements (`PaginatedResponse[EventResponse]`)
- [ ] Filtrage par `event_type`
- [ ] Permission AUMÔNIER pour créer/modifier des événements
- [ ] Validation métier : `end_time > start_time`
- [ ] Validation : pas d'événement dans le passé (configurable)
- [ ] Tests complets (unit, e2e, security, use-cases)

### 2.2 Module Affectations — Complétion ⏳

**Priorité : HAUTE** | **Effort : 3 sprints**

- [ ] `PATCH /assignments/{id}/accept` — Le servant accepte
- [ ] `PATCH /assignments/{id}/decline` — Le servant décline
- [ ] `PATCH /assignments/{id}/present` — Marquer présent (admin/aumônier)
- [ ] `PATCH /assignments/{id}/absent` — Marquer absent (admin/aumônier)
- [ ] `PATCH /assignments/{id}` — Modifier une affectation (admin)
- [ ] `DELETE /assignments/{id}` — Supprimer une affectation (admin)
- [ ] `GET /assignments/` — Liste paginée avec filtres (event, user, status)
- [ ] Machine à états : PENDING → ACCEPTED/DECLINED → PRESENT/ABSENT
- [ ] Empêcher les doublons (même servant, même événement)
- [ ] Notification au servant lors de l'affectation
- [ ] Historique des présences par servant
- [ ] Tests complets

### 2.3 Module Communication ⏳

**Priorité : MOYENNE** | **Effort : 2 sprints**

- [ ] Entité `Notification` (message, type, destinataire, statut, canal)
- [ ] `POST /communication/notify` — Envoyer une notification (admin)
- [ ] `GET /communication/history` — Historique des notifications
- [ ] Notification automatique lors d'une affectation
- [ ] Rappel automatique 24h avant un événement (job planifié)
- [ ] Notification au parent si servant absent
- [ ] Canal préféré par utilisateur (email, WhatsApp, les deux)
- [ ] Templates de messages configurables
- [ ] Intégration réelle Email (SMTP / SendGrid)
- [ ] Intégration réelle WhatsApp (Twilio)
- [ ] Tests complets

### 2.4 Migrations Alembic ⏳

**Priorité : HAUTE** | **Effort : 1 sprint**

- [ ] Migration initiale (`alembic revision --autogenerate -m "initial"`)
- [ ] Procédure de migration documentée
- [ ] Script de seed data (données de démo)
- [ ] Backup et restore documentés

### 2.5 Application Mobile Android 📱

**Priorité : HAUTE** | **Effort : 4 sprints**

- [ ] Architecture MVVM + Jetpack Compose
- [ ] Écran login (email + téléphone)
- [ ] Écran inscription
- [ ] Écran profil (consultation + modification)
- [ ] Écran liste événements (calendrier)
- [ ] Écran détail événement + affectations
- [ ] Écran mes affectations (accept/decline)
- [ ] Notifications push (Firebase Cloud Messaging)
- [ ] Gestion offline (cache local)
- [ ] Thème sombre

### 2.6 Qualité et Documentation ⏳

**Priorité : MOYENNE** | **Effort : 1 sprint**

- [ ] Couverture de tests ≥ 80%
- [ ] Documentation API OpenAPI/Swagger complète
- [ ] Guide de déploiement production
- [ ] Guide de contribution
- [ ] Changelog automatique

---

## Phase 3 : V1 — Enrichissement 🚀

> Objectif : fonctionnalités avancées pour une gestion optimale.

### 3.1 Gestion des Groupes

**Effort : 2 sprints**

- [ ] Entité `Group` (nom, description, tranche d'âge)
- [ ] Association servants ↔ groupes (many-to-many)
- [ ] Affectation par groupe (affecter un groupe entier à un événement)
- [ ] Filtrage des servants par groupe
- [ ] Chef de groupe (servant référent)

### 3.2 Planning Automatique

**Effort : 3 sprints**

- [ ] Algorithme de rotation équitable
- [ ] Prise en compte des disponibilités déclarées
- [ ] Prise en compte de l'historique de présence
- [ ] Gestion des conflits (même servant, même horaire)
- [ ] Suggestion automatique d'affectations
- [ ] Validation manuelle par l'admin/aumônier

### 3.3 Statistiques et Dashboard

**Effort : 2 sprints**

- [ ] Taux de présence par servant
- [ ] Taux de présence par événement
- [ ] Classement des servants les plus assidus
- [ ] Graphiques d'évolution (mensuel, annuel)
- [ ] Export PDF/Excel
- [ ] Dashboard admin web (React ou Vue.js)

### 3.4 Calendrier Partagé

**Effort : 1 sprint**

- [ ] Export iCal (.ics) des événements
- [ ] Synchronisation Google Calendar
- [ ] Lien de calendrier partageable

### 3.5 Application iOS

**Effort : 3 sprints**

- [ ] Port de l'app Android vers iOS (SwiftUI ou Flutter)
- [ ] Notifications push iOS (APNs)
- [ ] Publication App Store

### 3.6 Monitoring Production

**Effort : 1 sprint**

- [ ] Endpoint `/metrics` (Prometheus)
- [ ] Dashboard Grafana (latence, erreurs, DB)
- [ ] Alerting (taux d'erreur, latence P99)
- [ ] Logs centralisés (Loki ou ELK)
- [ ] Healthcheck avancé (DB, Redis, services externes)

### 3.7 Gestion des Fichiers

**Effort : 1 sprint**

- [ ] Upload photo de profil (Cloudflare R2)
- [ ] Upload documents (attestations, certificats)
- [ ] Redimensionnement d'images
- [ ] Quota de stockage par utilisateur

---

## Phase 4 : V2 — Mise à l'Échelle 🌍

> Objectif : solution multi-paroisse et écosystème complet.

### 4.1 Multi-Paroisse

- [ ] Entité `Parish` (nom, adresse, diocèse)
- [ ] Isolation des données par paroisse (tenant)
- [ ] Admin par paroisse
- [ ] Super-admin diocésain
- [ ] Transfert de servants entre paroisses

### 4.2 API Publique

- [ ] Versioning API (v1, v2)
- [ ] API Keys pour intégrations tierces
- [ ] Rate limiting par API Key
- [ ] Documentation Swagger publique
- [ ] Webhook pour les événements

### 4.3 PWA / Application Web

- [ ] Interface web responsive (React/Next.js)
- [ ] Mode hors-ligne (Service Worker)
- [ ] Installation sur l'écran d'accueil
- [ ] Même base de code que l'app mobile (ou Flutter Web)

### 4.4 Analytics et Intelligence

- [ ] Prédiction des absences (ML simple)
- [ ] Suggestion de rôles basée sur l'expérience
- [ ] Rapport automatique hebdomadaire par email
- [ ] Gamification (badges, niveaux)

### 4.5 Intégrations Externes

- [ ] Calendrier liturgique automatique (API Missale Romanum)
- [ ] SMS en fallback (si WhatsApp indisponible)
- [ ] Intégration ERP paroissial (si existant)
- [ ] QR Code pour la validation de présence

---

## Priorités Techniques Transversales

### Sécurité (continu)

| Tâche | Phase |
|---|---|
| Audit de sécurité externe | V0 |
| Rotation automatique des JWT secrets | V1 |
| 2FA pour les admins | V1 |
| Chiffrement des données sensibles au repos | V1 |
| Conformité RGPD (suppression de données) | V0 |
| Penetration testing | V1 |

### Performance (continu)

| Tâche | Phase |
|---|---|
| Index BDD optimisés | V0 |
| Cache Redis pour les listings | V0 |
| Pagination cursor-based (pour grands volumes) | V1 |
| CDN pour les fichiers statiques | V1 |
| Connection pooling optimisé | V0 |
| Load testing avec Locust | V1 |

### Infrastructure (continu)

| Tâche | Phase |
|---|---|
| Backup automatisé PostgreSQL | V0 |
| SSL/TLS (Let's Encrypt) | V0 |
| Reverse proxy (Nginx/Caddy) | V0 |
| Container orchestration (Docker Swarm) | V1 |
| Kubernetes (si scale nécessaire) | V2 |
| Blue-green deployment | V1 |

---

## Estimation Temporelle

| Phase | Durée estimée | Équipe | Livrables |
|---|---|---|---|
| **MVP** | ✅ Terminé | 1 développeur | Auth + Users + CI/CD |
| **V0** | 10-12 semaines | 1-2 développeurs | Backend complet + Mobile Android |
| **V1** | 12-16 semaines | 2-3 développeurs | Groupes + Planning + Stats + iOS |
| **V2** | 16-20 semaines | 3-4 développeurs | Multi-paroisse + Web + Analytics |

---

## Métriques de Succès

### V0
- [ ] 100% des fonctionnalités CRUD opérationnelles
- [ ] ≥ 80% de couverture de tests
- [ ] Temps de réponse API < 200ms (P95)
- [ ] Zéro vulnérabilité critique (Bandit + pip-audit)
- [ ] Application Android sur Play Store (beta)

### V1
- [ ] ≥ 90% de couverture de tests
- [ ] 10+ paroisses pilotes
- [ ] Taux d'adoption > 60% des servants ciblés
- [ ] Uptime > 99.5%

### V2
- [ ] 100+ paroisses
- [ ] API publique avec 3+ intégrations
- [ ] Application web + mobile multiplateforme
- [ ] Score Lighthouse > 90

---

## Dettes Techniques Identifiées

| Dette | Priorité | Phase de résolution |
|---|---|---|
| `datetime.utcnow()` → `datetime.now(timezone.utc)` | Basse | V0 |
| `from sqlalchemy import select` dans `admin.py` | Haute | V0 |
| Rate limiter en mémoire → Redis | Haute | V0 |
| Brute-force en mémoire → Redis | Haute | V0 |
| Tests schema phone validation (Pydantic v2 order) | Basse | V0 |
| `communication.py` est un stub | Haute | V0 |
| Pas de migration Alembic initiale | Haute | V0 |
| `EventService` sans méthode `update_event` | Haute | V0 |
| `AssignmentService` sans accept/decline | Haute | V0 |
| Email service est un mock | Moyenne | V0 |
| MyPy errors non résolues | Basse | V1 |

