# Plan d'Implémentation des Modules Responsables

Ce document détaille le plan d'implémentation complet pour tous les modules des responsables.

---

## Vue d'Ensemble

**7 modules à implémenter** :
1. ✅ ECONOME - Contributions financières
2. ✅ CENSEUR - Appels et discipline
3. ⏳ SECRETAIRE - Rapports et administration
4. ⏳ COMMISSAIRE_AUX_COMPTES - Audit financier
5. ⏳ CHARGE_LITURGIE - Formations liturgiques
6. ⏳ INTENDANTS - Gestion du matériel
7. ⏳ CHARGE_SPORT_CULTURE - Activités sportives et culturelles

---

## Phase 1 : Modules Financiers (ECONOME + COMMISSAIRE)

### Module ECONOME - Contributions

#### Entités ✅
- [x] `Contribution` - Paiement individuel
- [x] `MonthlyContributionSummary` - Résumé mensuel
- [x] `FinancialReport` - Rapport financier

#### Schémas Pydantic
- [ ] `ContributionCreate` - Créer une contribution
- [ ] `ContributionUpdate` - Modifier une contribution
- [ ] `ContributionResponse` - Réponse API
- [ ] `FinancialReportRequest` - Paramètres du rapport
- [ ] `FinancialReportResponse` - Rapport complet

#### Repository
- [ ] `ContributionRepository`
  - create_contribution()
  - get_contribution()
  - list_contributions()
  - update_contribution()
  - delete_contribution()
  - get_monthly_summary()
  - generate_financial_report()

#### Service
- [ ] `ContributionService`
  - record_payment()
  - update_payment()
  - get_servant_contributions()
  - get_monthly_summary()
  - generate_financial_report()
  - calculate_expected_amount()
  - check_payment_status()

#### API Endpoints
- [ ] `POST /api/v1/contributions` - Enregistrer un paiement
- [ ] `GET /api/v1/contributions` - Liste des contributions
- [ ] `GET /api/v1/contributions/{id}` - Détail d'une contribution
- [ ] `PATCH /api/v1/contributions/{id}` - Modifier une contribution
- [ ] `DELETE /api/v1/contributions/{id}` - Supprimer une contribution
- [ ] `GET /api/v1/contributions/servant/{servant_id}` - Contributions d'un servant
- [ ] `GET /api/v1/contributions/summary/{month}/{year}` - Résumé mensuel
- [ ] `POST /api/v1/contributions/report` - Générer un rapport

#### Migration Alembic
- [ ] Table `contributions`
- [ ] Index sur `servant_id`, `month`, `year`

#### Tests
- [ ] Tests unitaires du service
- [ ] Tests e2e des endpoints
- [ ] Tests de permissions (ECONOME uniquement)

---

## Phase 2 : Module Discipline (CENSEUR)

### Module CENSEUR - Appels

#### Entités ✅
- [x] `AttendanceSession` - Session d'appel
- [x] `AttendanceRecord` - Enregistrement de présence
- [x] `ServantAttendanceStats` - Statistiques
- [x] `AttendanceReport` - Rapport de présence

#### Schémas Pydantic
- [ ] `AttendanceSessionCreate` - Créer une session
- [ ] `AttendanceSessionResponse` - Réponse session
- [ ] `AttendanceRecordCreate` - Marquer présence
- [ ] `AttendanceRecordUpdate` - Modifier présence
- [ ] `AttendanceRecordResponse` - Réponse présence
- [ ] `AttendanceReportRequest` - Paramètres du rapport

#### Repository
- [ ] `AttendanceRepository`
  - create_session()
  - get_session()
  - list_sessions()
  - create_record()
  - update_record()
  - get_servant_records()
  - calculate_stats()
  - generate_report()

#### Service
- [ ] `AttendanceService`
  - create_session()
  - mark_attendance()
  - update_attendance()
  - get_session_records()
  - get_servant_stats()
  - generate_report()
  - get_all_servants_list()

#### API Endpoints
- [ ] `POST /api/v1/attendance/sessions` - Créer une session
- [ ] `GET /api/v1/attendance/sessions` - Liste des sessions
- [ ] `GET /api/v1/attendance/sessions/{id}` - Détail session
- [ ] `POST /api/v1/attendance/sessions/{id}/records` - Marquer présence
- [ ] `PATCH /api/v1/attendance/records/{id}` - Modifier présence
- [ ] `GET /api/v1/attendance/servants/{id}/stats` - Stats d'un servant
- [ ] `POST /api/v1/attendance/report` - Générer rapport
- [ ] `GET /api/v1/attendance/servants/list` - Liste complète des servants

#### Migration Alembic
- [ ] Table `attendance_sessions`
- [ ] Table `attendance_records`
- [ ] Index sur `session_id`, `servant_id`

#### Tests
- [ ] Tests unitaires
- [ ] Tests e2e
- [ ] Tests permissions (CENSEUR/CENSEUR_ADJOINT)

---

## Phase 3 : Module Administration (SECRETAIRE)

### Module SECRETAIRE - Rapports

#### Entités
- [ ] `Report` - Rapport (réunion/activité)
- [ ] `ReportAttachment` - Pièce jointe
- [ ] `ReportParticipant` - Participant

#### Schémas Pydantic
- [ ] `ReportCreate`
- [ ] `ReportUpdate`
- [ ] `ReportResponse`
- [ ] `ReportPublish`

#### Repository
- [ ] `ReportRepository`

#### Service
- [ ] `ReportService`

#### API Endpoints
- [ ] `POST /api/v1/reports` - Créer un rapport
- [ ] `GET /api/v1/reports` - Liste des rapports
- [ ] `GET /api/v1/reports/{id}` - Détail
- [ ] `PATCH /api/v1/reports/{id}` - Modifier
- [ ] `POST /api/v1/reports/{id}/publish` - Publier
- [ ] `POST /api/v1/reports/{id}/attachments` - Ajouter pièce jointe
- [ ] `GET /api/v1/reports/{id}/export` - Export PDF

#### Migration Alembic
- [ ] Table `reports`
- [ ] Table `report_attachments`
- [ ] Table `report_participants`

---

## Phase 4 : Module Audit (COMMISSAIRE_AUX_COMPTES)

### Module COMMISSAIRE - Audit Financier

#### Entités
- [ ] `FinancialEntry` - Entrée financière
- [ ] `AuditReport` - Rapport d'audit

#### Schémas Pydantic
- [ ] `FinancialEntryCreate`
- [ ] `FinancialEntryResponse`
- [ ] `AuditReportRequest`

#### Repository
- [ ] `FinancialEntryRepository`

#### Service
- [ ] `AuditService`

#### API Endpoints
- [ ] `POST /api/v1/audit/entries` - Enregistrer entrée
- [ ] `GET /api/v1/audit/entries` - Liste des entrées
- [ ] `POST /api/v1/audit/report` - Générer rapport d'audit
- [ ] `GET /api/v1/audit/discrepancies` - Écarts détectés

#### Migration Alembic
- [ ] Table `financial_entries`

---

## Phase 5 : Module Formation (CHARGE_LITURGIE)

### Module CHARGE_LITURGIE - Formations

#### Entités
- [ ] `TrainingSession` - Session de formation
- [ ] `TrainingParticipation` - Participation
- [ ] `TrainingMaterial` - Matériel pédagogique

#### Schémas Pydantic
- [ ] `TrainingSessionCreate`
- [ ] `TrainingSessionResponse`
- [ ] `ParticipationCreate`

#### Repository
- [ ] `TrainingRepository`

#### Service
- [ ] `TrainingService`

#### API Endpoints
- [ ] `POST /api/v1/training/sessions` - Créer session
- [ ] `GET /api/v1/training/sessions` - Liste sessions
- [ ] `POST /api/v1/training/sessions/{id}/register` - S'inscrire
- [ ] `POST /api/v1/training/sessions/{id}/attendance` - Marquer présence
- [ ] `GET /api/v1/training/materials` - Bibliothèque de ressources

#### Migration Alembic
- [ ] Table `training_sessions`
- [ ] Table `training_participations`
- [ ] Table `training_materials`

---

## Phase 6 : Module Matériel (INTENDANTS)

### Module INTENDANTS - Gestion du Matériel

#### Entités
- [ ] `MaterialItem` - Article de matériel
- [ ] `CleaningTask` - Tâche de nettoyage
- [ ] `AubeTask` - Tâche lavage/repassage aubes

#### Schémas Pydantic
- [ ] `MaterialItemCreate`
- [ ] `CleaningTaskCreate`
- [ ] `AubeTaskCreate`

#### Repository
- [ ] `MaterialRepository`

#### Service
- [ ] `MaterialService`

#### API Endpoints
- [ ] `POST /api/v1/material/items` - Ajouter article
- [ ] `GET /api/v1/material/items` - Inventaire
- [ ] `POST /api/v1/material/cleaning-tasks` - Créer tâche nettoyage
- [ ] `POST /api/v1/material/aube-tasks` - Créer tâche aubes
- [ ] `PATCH /api/v1/material/tasks/{id}/complete` - Marquer terminé

#### Migration Alembic
- [ ] Table `material_items`
- [ ] Table `cleaning_tasks`
- [ ] Table `cleaning_task_assignments`
- [ ] Table `aube_tasks`
- [ ] Table `aube_task_assignments`

---

## Phase 7 : Module Sport/Culture (CHARGE_SPORT_CULTURE)

### Module CHARGE_SPORT_CULTURE - Activités

#### Entités
- [ ] `SportCultureEvent` - Événement sportif/culturel
- [ ] `EventParticipation` - Participation
- [ ] `EventResult` - Résultat (scores, etc.)

#### Schémas Pydantic
- [ ] `SportCultureEventCreate`
- [ ] `EventParticipationCreate`

#### Repository
- [ ] `SportCultureRepository`

#### Service
- [ ] `SportCultureService`

#### API Endpoints
- [ ] `POST /api/v1/sport-culture/events` - Créer événement
- [ ] `GET /api/v1/sport-culture/events` - Liste événements
- [ ] `POST /api/v1/sport-culture/events/{id}/register` - S'inscrire
- [ ] `POST /api/v1/sport-culture/events/{id}/results` - Enregistrer résultats

#### Migration Alembic
- [ ] Table `sport_culture_events`
- [ ] Table `event_participations`
- [ ] Table `event_results`

---

## Fonctionnalités Transversales

### Notifications
- [ ] Service de notification unifié
- [ ] Templates pour chaque type d'événement
- [ ] Broadcast à tous les utilisateurs
- [ ] Notifications individuelles

### Exports PDF
- [ ] Service d'export PDF
- [ ] Intégration logo en filigrane
- [ ] Templates pour chaque type de rapport

### Permissions
- [ ] Décorateurs de permissions par rôle
- [ ] Middleware de vérification
- [ ] Tests de permissions pour chaque endpoint

---

## Estimation Temporelle

| Phase | Module | Durée estimée | Complexité |
|-------|--------|---------------|------------|
| 1 | ECONOME | 3-4 jours | Moyenne |
| 2 | CENSEUR | 2-3 jours | Faible |
| 3 | SECRETAIRE | 2-3 jours | Faible |
| 4 | COMMISSAIRE | 2-3 jours | Moyenne |
| 5 | CHARGE_LITURGIE | 3-4 jours | Moyenne |
| 6 | INTENDANTS | 4-5 jours | Élevée |
| 7 | CHARGE_SPORT_CULTURE | 2-3 jours | Faible |
| **Total** | **7 modules** | **18-25 jours** | - |

---

## Prochaines Étapes

1. ✅ Créer les entités de base (ECONOME, CENSEUR)
2. ⏳ Créer les schémas Pydantic
3. ⏳ Implémenter les repositories
4. ⏳ Implémenter les services
5. ⏳ Créer les endpoints API
6. ⏳ Créer les migrations Alembic
7. ⏳ Écrire les tests
8. ⏳ Documenter les API

**Commençons par le module ECONOME (Phase 1) !**
