# Actions Disponibles par Rôle - Backend ServantAssist

**Date** : 11 février 2026  
**Version** : 1.0

---

## Vue d'Ensemble

Ce document liste toutes les actions disponibles dans le backend ServantAssist, organisées par rôle utilisateur. Chaque action indique l'endpoint API, la méthode HTTP, et les permissions requises.

---

## Légende

- 🔓 **Public** : Accessible sans authentification
- 🔐 **Authentifié** : Nécessite une authentification (tout rôle)
- 👤 **Self** : L'utilisateur peut agir sur ses propres données
- 🔒 **Rôle spécifique** : Nécessite un rôle particulier

---

## Table des Matières

1. [Actions Publiques (Sans Authentification)](#1-actions-publiques)
2. [Actions Communes (Tous Utilisateurs Authentifiés)](#2-actions-communes)
3. [Actions ADMIN](#3-actions-admin)
4. [Actions AUMÔNIER](#4-actions-aumônier)
5. [Actions SERVANT](#5-actions-servant)
6. [Actions PARENT](#6-actions-parent)
7. [Actions ECONOME](#7-actions-econome)
8. [Actions CENSEUR](#8-actions-censeur)
9. [Actions SECRETAIRE](#9-actions-secretaire)
10. [Actions COMMISSAIRE_AUX_COMPTES](#10-actions-commissaire-aux-comptes)
11. [Actions CHARGE_LITURGIE](#11-actions-charge-liturgie)
12. [Actions INTENDANTS](#12-actions-intendants)
13. [Actions CHARGE_SPORT_CULTURE](#13-actions-charge-sport-culture)
14. [Résumé par Rôle](#14-résumé-par-rôle)

---


## 1. Actions Publiques (Sans Authentification)

### 🔓 Authentification

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Connexion email | POST | `/api/v1/auth/login` | Connexion ADMIN/AUMÔNIER avec email + mot de passe |
| Connexion téléphone | POST | `/api/v1/auth/login/phone` | Connexion SERVANT/PARENT avec téléphone + mot de passe |
| Inscription SERVANT | POST | `/api/v1/auth/register` | Auto-inscription en tant que SERVANT (pas de code requis) |
| Inscription PARENT | POST | `/api/v1/auth/register` | Inscription PARENT avec code d'invitation |
| Renouveler token | POST | `/api/v1/auth/refresh` | Renouveler les tokens JWT avec refresh_token |
| Mot de passe oublié | POST | `/api/v1/auth/forgot-password` | Demander réinitialisation du mot de passe |
| Réinitialiser mot de passe | POST | `/api/v1/auth/reset-password` | Réinitialiser avec token reçu par email |

---

## 2. Actions Communes (Tous Utilisateurs Authentifiés)

### 🔐 Gestion de Profil

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Voir mon profil | GET | `/api/v1/users/me` | Récupérer mes informations |
| Modifier mon profil | PATCH | `/api/v1/users/me` | Modifier nom, prénom, téléphone |
| Changer mon mot de passe | PATCH | `/api/v1/users/me/password` | Changer mon mot de passe |
| Uploader ma photo | POST | `/api/v1/users/me/photo` | Ajouter/remplacer ma photo de profil |
| Supprimer ma photo | DELETE | `/api/v1/users/me/photo` | Supprimer ma photo de profil |

### 🔐 Consultation (Lecture Seule)

| Module | Actions Disponibles |
|--------|---------------------|
| **Contributions** | Consulter mes contributions, voir les statistiques |
| **Appels** | Consulter mes présences, voir mes statistiques |
| **Rapports** | Consulter les rapports publiés |
| **Formations** | Consulter les sessions, matériels publics, mes participations |
| **Matériel** | Consulter l'inventaire, les tâches, l'historique |
| **Sport/Culture** | Consulter les événements, résultats, équipes, mes participations |

---


## 3. Actions ADMIN

### 🔒 Gestion des Utilisateurs (26 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Lister utilisateurs | GET | `/api/v1/users/` | Liste paginée avec filtres (rôle, statut, recherche) |
| Voir utilisateur | GET | `/api/v1/users/{user_id}` | Détail d'un utilisateur |
| Modifier utilisateur | PATCH | `/api/v1/users/{user_id}` | Modifier nom, email, téléphone, statut |
| Activer compte | PATCH | `/api/v1/users/{user_id}/activate` | Réactiver un compte désactivé |
| Désactiver compte | PATCH | `/api/v1/users/{user_id}/deactivate` | Désactiver un compte |
| Réinitialiser mot de passe | POST | `/api/v1/users/{user_id}/reset-password` | Forcer nouveau mot de passe |
| Supprimer utilisateur | DELETE | `/api/v1/users/{user_id}` | Supprimer définitivement |

### 🔒 Gestion des Invitations (3 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer invitation | POST | `/api/v1/admin/invitations` | Générer code pour PARENT/AUMÔNIER |
| Lister invitations | GET | `/api/v1/admin/invitations` | Voir toutes mes invitations créées |
| Révoquer invitation | DELETE | `/api/v1/admin/invitations/{id}` | Annuler un code d'invitation |

### 🔒 Création Directe d'Utilisateurs (3 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer ADMIN | POST | `/api/v1/admin/users/admin` | Créer un administrateur (unique) |
| Créer AUMÔNIER | POST | `/api/v1/admin/users/aumônier` | Créer un aumônier (unique) |
| Créer PARENT | POST | `/api/v1/admin/users/parent` | Créer un parent directement |

### 🔒 Accès Complet à Tous les Modules

L'ADMIN a accès en lecture à tous les modules mais ne peut pas effectuer les actions métier réservées aux responsables spécifiques.

**Total ADMIN : ~32 actions spécifiques + consultation de tous les modules**

---

## 4. Actions AUMÔNIER

### 🔒 Supervision Générale

L'AUMÔNIER a un accès en lecture à tous les modules pour supervision, mais ne peut pas effectuer les actions métier réservées aux responsables.

| Module | Accès |
|--------|-------|
| Contributions | Lecture seule (consultation) |
| Appels | Lecture seule (consultation) |
| Rapports | Lecture seule (consultation) |
| Entrées financières | Lecture seule (consultation) |
| Formations | Lecture seule (consultation) |
| Matériel | Lecture seule (consultation) |
| Sport/Culture | Lecture seule (consultation) |

**Total AUMÔNIER : Consultation de tous les modules (lecture seule)**

---


## 5. Actions SERVANT

### 👤 Gestion Personnelle

| Action | Description |
|--------|-------------|
| Voir mon profil | Consulter mes informations |
| Modifier mon profil | Mettre à jour mes données |
| Changer mot de passe | Modifier mon mot de passe |
| Gérer ma photo | Upload/suppression photo de profil |

### 🔐 Consultation des Modules

| Module | Actions Disponibles |
|--------|---------------------|
| **Contributions** | Voir mes contributions, statistiques personnelles |
| **Appels** | Voir mes présences, taux de présence |
| **Rapports** | Lire les rapports publiés |
| **Formations** | Voir sessions, s'inscrire, consulter mes participations |
| **Matériel** | Voir inventaire, tâches assignées, marquer tâches terminées |
| **Sport/Culture** | Voir événements, mes participations, résultats, équipes |

**Total SERVANT : ~15 actions (profil + consultation modules)**

---

## 6. Actions PARENT

### 👤 Gestion Personnelle

Identique aux SERVANTS (profil, mot de passe, photo)

### 🔐 Suivi de son Enfant

| Action | Description |
|--------|-------------|
| Voir contributions enfant | Consulter les contributions de son enfant |
| Voir présences enfant | Consulter les présences de son enfant |
| Voir participations enfant | Consulter les activités de son enfant |

**Total PARENT : ~10 actions (profil + suivi enfant)**

---

## 7. Actions ECONOME

### 🔒 Gestion des Contributions (9 endpoints)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Enregistrer contribution | POST | `/api/v1/contributions` | Enregistrer paiement (hebdo/mensuel) |
| Lister contributions | GET | `/api/v1/contributions` | Liste avec filtres (servant, période, mode) |
| Voir contribution | GET | `/api/v1/contributions/{id}` | Détail d'une contribution |
| Modifier contribution | PATCH | `/api/v1/contributions/{id}` | Corriger montant, date, mode |
| Supprimer contribution | DELETE | `/api/v1/contributions/{id}` | Annuler une contribution |
| Contributions par servant | GET | `/api/v1/contributions/servant/{id}` | Historique d'un servant |
| Résumé mensuel | GET | `/api/v1/contributions/summary/monthly` | Résumé du mois |
| Statistiques servant | GET | `/api/v1/contributions/servant/{id}/stats` | Stats d'un servant |
| Générer rapport | POST | `/api/v1/contributions/report` | Rapport de période avec watermark |

**Total ECONOME : 9 actions**

---


## 8. Actions CENSEUR

### 🔒 Gestion des Appels (8 endpoints)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer session d'appel | POST | `/api/v1/attendance-sessions` | Créer appel (samedi 06h15) |
| Lister sessions | GET | `/api/v1/attendance-sessions` | Liste avec filtres (date, statut) |
| Voir session | GET | `/api/v1/attendance-sessions/{id}` | Détail d'une session |
| Modifier session | PATCH | `/api/v1/attendance-sessions/{id}` | Modifier date, notes |
| Marquer présence | POST | `/api/v1/attendance-sessions/{id}/mark` | Marquer PRESENT/ABSENT/LATE/EXCUSED |
| Clôturer session | POST | `/api/v1/attendance-sessions/{id}/close` | Finaliser l'appel |
| Statistiques servant | GET | `/api/v1/attendance-sessions/servant/{id}/stats` | Stats de présence |
| Générer rapport | POST | `/api/v1/attendance-sessions/report` | Rapport de période avec watermark |

**Total CENSEUR : 8 actions**

---

## 9. Actions SECRETAIRE

### 🔒 Gestion des Rapports (11 endpoints)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer rapport | POST | `/api/v1/reports` | Créer rapport REUNION/ACTIVITE |
| Lister rapports | GET | `/api/v1/reports` | Liste avec filtres (type, statut, date) |
| Voir rapport | GET | `/api/v1/reports/{id}` | Détail d'un rapport |
| Modifier rapport | PATCH | `/api/v1/reports/{id}` | Modifier contenu, participants |
| Supprimer rapport | DELETE | `/api/v1/reports/{id}` | Supprimer un rapport |
| Ajouter pièce jointe | POST | `/api/v1/reports/{id}/attachments` | Ajouter fichier |
| Supprimer pièce jointe | DELETE | `/api/v1/reports/{id}/attachments/{attachment_id}` | Retirer fichier |
| Publier rapport | POST | `/api/v1/reports/{id}/publish` | Rendre visible à tous |
| Archiver rapport | POST | `/api/v1/reports/{id}/archive` | Archiver |
| Rapports publiés | GET | `/api/v1/reports/published` | Liste des rapports publiés |
| Générer résumé | POST | `/api/v1/reports/summary` | Résumé de période avec watermark |

**Total SECRETAIRE : 11 actions**

---

## 10. Actions COMMISSAIRE AUX COMPTES

### 🔒 Audit Financier (13 endpoints)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer entrée financière | POST | `/api/v1/financial-entries` | Enregistrer RECETTE/DEPENSE |
| Lister entrées | GET | `/api/v1/financial-entries` | Liste avec filtres (catégorie, source, période) |
| Voir entrée | GET | `/api/v1/financial-entries/{id}` | Détail d'une entrée |
| Modifier entrée | PATCH | `/api/v1/financial-entries/{id}` | Corriger montant, catégorie |
| Supprimer entrée | DELETE | `/api/v1/financial-entries/{id}` | Supprimer une entrée |
| Vérifier entrée | POST | `/api/v1/financial-entries/{id}/verify` | Marquer VERIFIE/REJETE |
| Ajouter pièce jointe | POST | `/api/v1/financial-entries/{id}/attachments` | Ajouter justificatif |
| Supprimer pièce jointe | DELETE | `/api/v1/financial-entries/{id}/attachments/{attachment_id}` | Retirer fichier |
| Entrées non vérifiées | GET | `/api/v1/financial-entries/unverified` | Liste à vérifier |
| Entrées rejetées | GET | `/api/v1/financial-entries/rejected` | Liste des rejets |
| Résumé financier | GET | `/api/v1/financial-entries/summary` | Résumé recettes/dépenses |
| Statistiques | GET | `/api/v1/financial-entries/stats` | Stats par catégorie/source |
| Générer rapport audit | POST | `/api/v1/financial-entries/audit-report` | Rapport d'audit avec watermark |

**Total COMMISSAIRE : 13 actions**

---


## 11. Actions CHARGE LITURGIE

### 🔒 Gestion des Formations (20 endpoints)

#### Sessions de Formation (6 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer session | POST | `/api/v1/training/sessions` | Planifier formation (niveau, date, lieu) |
| Lister sessions | GET | `/api/v1/training/sessions` | Liste avec filtres (niveau, statut, date) |
| Voir session | GET | `/api/v1/training/sessions/{id}` | Détail d'une session |
| Modifier session | PATCH | `/api/v1/training/sessions/{id}` | Modifier date, lieu, max participants |
| Supprimer session | DELETE | `/api/v1/training/sessions/{id}` | Annuler une session |
| Mes sessions | GET | `/api/v1/training/sessions/me/list` | Sessions que j'anime |

#### Participations (8 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Inscrire servant | POST | `/api/v1/training/sessions/{id}/register` | Inscrire un servant |
| Inscription par lot | POST | `/api/v1/training/sessions/{id}/register-batch` | Inscrire plusieurs servants |
| Liste participants | GET | `/api/v1/training/sessions/{id}/participants` | Voir les inscrits |
| Marquer présence | POST | `/api/v1/training/participations/{id}/attendance` | Marquer PRESENT/ABSENT/EXCUSE |
| Évaluer participant | POST | `/api/v1/training/participations/{id}/evaluate` | Noter sur 100 + commentaire |
| Annuler inscription | DELETE | `/api/v1/training/participations/{id}` | Retirer un participant |
| Participations servant | GET | `/api/v1/training/servants/{id}/participations` | Historique d'un servant |
| Stats servant | GET | `/api/v1/training/servants/{id}/stats` | Statistiques de formation |

#### Matériels Pédagogiques (5 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer matériel | POST | `/api/v1/training/materials` | Ajouter ressource (doc, vidéo, quiz) |
| Lister matériels | GET | `/api/v1/training/materials` | Liste avec filtres (type, niveau) |
| Voir matériel | GET | `/api/v1/training/materials/{id}` | Détail d'une ressource |
| Modifier matériel | PATCH | `/api/v1/training/materials/{id}` | Mettre à jour |
| Supprimer matériel | DELETE | `/api/v1/training/materials/{id}` | Retirer une ressource |

#### Rapports (1 action)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Générer rapport | POST | `/api/v1/training/report` | Rapport de formation avec watermark |

**Total CHARGE_LITURGIE : 20 actions**

---


## 12. Actions INTENDANTS

### 🔒 Gestion du Matériel (25 endpoints)

#### Inventaire (6 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer article | POST | `/api/v1/material/items` | Ajouter matériel (9 catégories) |
| Lister articles | GET | `/api/v1/material/items` | Liste avec filtres (catégorie, état) |
| Voir article | GET | `/api/v1/material/items/{id}` | Détail d'un article |
| Modifier article | PATCH | `/api/v1/material/items/{id}` | Mettre à jour quantité, état |
| Supprimer article | DELETE | `/api/v1/material/items/{id}` | Retirer du stock |
| Articles à maintenir | GET | `/api/v1/material/items/maintenance/needed` | Liste nécessitant maintenance |

#### Tâches de Nettoyage (7 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer tâche | POST | `/api/v1/material/cleaning-tasks` | Planifier nettoyage/lavage/réparation |
| Lister tâches | GET | `/api/v1/material/cleaning-tasks` | Liste avec filtres (type, statut) |
| Voir tâche | GET | `/api/v1/material/cleaning-tasks/{id}` | Détail d'une tâche |
| Modifier tâche | PATCH | `/api/v1/material/cleaning-tasks/{id}` | Mettre à jour |
| Marquer terminée | POST | `/api/v1/material/cleaning-tasks/{id}/complete` | Marquer comme terminée |
| Valider tâche | POST | `/api/v1/material/cleaning-tasks/{id}/validate` | Valider le travail |
| Supprimer tâche | DELETE | `/api/v1/material/cleaning-tasks/{id}` | Annuler une tâche |

#### Assignations (4 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Assigner servant | POST | `/api/v1/material/cleaning-tasks/{id}/assign` | Assigner un servant |
| Assignation par lot | POST | `/api/v1/material/cleaning-tasks/{id}/assign-batch` | Assigner plusieurs servants |
| Assignations servant | GET | `/api/v1/material/servants/{id}/assignments` | Tâches d'un servant |
| Retirer assignation | DELETE | `/api/v1/material/assignments/{id}` | Retirer un servant |

#### Tâches d'Aubes (6 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer tâche aubes | POST | `/api/v1/material/aube-tasks` | Planifier lavage/repassage avec broadcast |
| Lister tâches aubes | GET | `/api/v1/material/aube-tasks` | Liste des tâches d'aubes |
| Voir tâche aubes | GET | `/api/v1/material/aube-tasks/{id}` | Détail |
| Modifier tâche aubes | PATCH | `/api/v1/material/aube-tasks/{id}` | Mettre à jour |
| Marquer terminée | POST | `/api/v1/material/aube-tasks/{id}/complete` | Marquer comme terminée |
| Valider tâche aubes | POST | `/api/v1/material/aube-tasks/{id}/validate` | Valider |
| Supprimer tâche aubes | DELETE | `/api/v1/material/aube-tasks/{id}` | Annuler |

#### Maintenance et Rapports (2 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Ajouter maintenance | POST | `/api/v1/material/items/{id}/maintenance` | Enregistrer intervention + coût |
| Historique maintenance | GET | `/api/v1/material/items/{id}/maintenance` | Historique d'un article |
| Générer rapport | POST | `/api/v1/material/report` | Rapport de période avec watermark |
| Statistiques | GET | `/api/v1/material/stats` | Stats globales |

**Total INTENDANTS : 25 actions**

---


## 13. Actions CHARGE SPORT CULTURE

### 🔒 Gestion des Activités Sportives et Culturelles (26 endpoints)

#### Événements (7 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer événement | POST | `/api/v1/sport-culture/events` | Planifier journée sportive/sortie culturelle |
| Lister événements | GET | `/api/v1/sport-culture/events` | Liste avec filtres (type, statut, date) |
| Voir événement | GET | `/api/v1/sport-culture/events/{id}` | Détail d'un événement |
| Modifier événement | PATCH | `/api/v1/sport-culture/events/{id}` | Mettre à jour |
| Supprimer événement | DELETE | `/api/v1/sport-culture/events/{id}` | Annuler un événement |
| Événements à venir | GET | `/api/v1/sport-culture/events/upcoming/list` | Prochains événements |

#### Participations (9 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Inscrire servant | POST | `/api/v1/sport-culture/events/{id}/register` | Inscrire à un événement |
| Inscription par lot | POST | `/api/v1/sport-culture/events/{id}/register-batch` | Inscrire plusieurs servants |
| Liste participants | GET | `/api/v1/sport-culture/events/{id}/participants` | Voir les inscrits |
| Marquer présence | POST | `/api/v1/sport-culture/participations/{id}/attendance` | Marquer PRESENT/ABSENT/EXCUSE |
| Marquer paiement | POST | `/api/v1/sport-culture/participations/{id}/payment` | Enregistrer paiement |
| Annuler inscription | DELETE | `/api/v1/sport-culture/participations/{id}` | Retirer un participant |
| Participations servant | GET | `/api/v1/sport-culture/servants/{id}/participations` | Historique d'un servant |
| Stats servant | GET | `/api/v1/sport-culture/servants/{id}/stats` | Statistiques de participation |

#### Résultats (3 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Ajouter résultat | POST | `/api/v1/sport-culture/events/{id}/results` | Enregistrer score/classement |
| Voir résultats | GET | `/api/v1/sport-culture/events/{id}/results` | Résultats d'un événement |
| Supprimer résultat | DELETE | `/api/v1/sport-culture/results/{id}` | Retirer un résultat |

#### Équipes (5 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Créer équipe | POST | `/api/v1/sport-culture/events/{id}/teams` | Former une équipe |
| Lister équipes | GET | `/api/v1/sport-culture/events/{id}/teams` | Équipes d'un événement |
| Modifier équipe | PATCH | `/api/v1/sport-culture/teams/{id}` | Changer capitaine/membres |
| Supprimer équipe | DELETE | `/api/v1/sport-culture/teams/{id}` | Dissoudre une équipe |

#### Rapports et Statistiques (2 actions)

| Action | Méthode | Endpoint | Description |
|--------|---------|----------|-------------|
| Générer rapport | POST | `/api/v1/sport-culture/report` | Rapport d'activités avec watermark |
| Statistiques globales | GET | `/api/v1/sport-culture/stats` | Stats générales |

**Total CHARGE_SPORT_CULTURE : 26 actions**

---


## 14. Résumé par Rôle

### Tableau Récapitulatif

| Rôle | Actions Spécifiques | Consultation | Total Approximatif |
|------|---------------------|--------------|-------------------|
| **🔓 Public** | 7 (auth) | - | 7 |
| **🔐 Authentifié** | 5 (profil) | Tous modules | ~20 |
| **👤 SERVANT** | 5 (profil) | Tous modules | ~15 |
| **👤 PARENT** | 5 (profil) | Suivi enfant | ~10 |
| **🔒 ADMIN** | 32 (gestion) | Tous modules | ~50 |
| **🔒 AUMÔNIER** | 0 (supervision) | Tous modules | ~15 |
| **🔒 ECONOME** | 9 | Contributions | ~15 |
| **🔒 CENSEUR** | 8 | Appels | ~15 |
| **🔒 SECRETAIRE** | 11 | Rapports | ~20 |
| **🔒 COMMISSAIRE** | 13 | Finances | ~20 |
| **🔒 CHARGE_LITURGIE** | 20 | Formations | ~25 |
| **🔒 INTENDANTS** | 25 | Matériel | ~30 |
| **🔒 CHARGE_SPORT_CULTURE** | 26 | Sport/Culture | ~30 |

### Statistiques Globales

- **Total endpoints API** : 112
- **Modules métier** : 7
- **Rôles utilisateurs** : 13 (incluant adjoints)
- **Actions publiques** : 7
- **Actions authentifiées communes** : ~20

---

## 15. Matrice de Permissions Détaillée

### Légende des Permissions

| Symbole | Signification |
|---------|---------------|
| ✅ | Accès complet (lecture + écriture) |
| 👁️ | Lecture seule |
| ❌ | Pas d'accès |
| 👤 | Accès à ses propres données uniquement |

### Matrice par Module

| Module | ADMIN | AUMÔNIER | SERVANT | PARENT | ECONOME | CENSEUR | SECRETAIRE | COMMISSAIRE | CHARGE_LITURGIE | INTENDANTS | CHARGE_SPORT_CULTURE |
|--------|-------|----------|---------|--------|---------|---------|------------|-------------|-----------------|------------|---------------------|
| **Utilisateurs** | ✅ | 👁️ | 👤 | 👤 | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| **Invitations** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Contributions** | 👁️ | 👁️ | 👤 | 👁️ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Appels** | 👁️ | 👁️ | 👤 | 👁️ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Rapports** | 👁️ | 👁️ | 👁️ | 👁️ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Finances** | 👁️ | 👁️ | 👁️ | 👁️ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Formations** | 👁️ | 👁️ | 👁️ | 👁️ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Matériel** | 👁️ | 👁️ | 👁️ | 👁️ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Sport/Culture** | 👁️ | 👁️ | 👁️ | 👁️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 16. Cas d'Usage par Rôle

### 🔒 ADMIN - Administrateur Système

**Responsabilités** :
- Gestion des utilisateurs et des accès
- Création des comptes ADMIN, AUMÔNIER, PARENT
- Génération des codes d'invitation
- Supervision générale du système

**Actions quotidiennes** :
1. Créer des comptes utilisateurs
2. Gérer les invitations pour les parents
3. Activer/désactiver des comptes
4. Consulter les statistiques globales

---

### 🔒 AUMÔNIER - Supervision Spirituelle

**Responsabilités** :
- Supervision de toutes les activités
- Consultation des rapports et statistiques
- Accompagnement spirituel des servants

**Actions quotidiennes** :
1. Consulter les rapports de réunions
2. Voir les statistiques de présence
3. Suivre les formations liturgiques
4. Superviser les activités

---

### 👤 SERVANT - Membre Actif

**Responsabilités** :
- Participer aux activités
- Maintenir son profil à jour
- Consulter ses statistiques

**Actions quotidiennes** :
1. Voir mes présences et contributions
2. M'inscrire aux formations
3. Consulter les événements sportifs
4. Voir mes tâches de nettoyage

---

### 👤 PARENT - Suivi de l'Enfant

**Responsabilités** :
- Suivre l'activité de son enfant
- Consulter les contributions et présences

**Actions quotidiennes** :
1. Voir les présences de mon enfant
2. Consulter ses contributions
3. Suivre ses participations aux activités

---

### 🔒 ECONOME - Gestion Financière

**Responsabilités** :
- Enregistrer les contributions
- Générer les rapports financiers
- Suivre les paiements

**Actions hebdomadaires** :
1. Enregistrer les contributions du samedi
2. Générer le résumé mensuel
3. Suivre les servants en retard de paiement

---

### 🔒 CENSEUR - Discipline et Présence

**Responsabilités** :
- Gérer les appels hebdomadaires
- Marquer les présences
- Générer les rapports de présence

**Actions hebdomadaires** :
1. Créer la session d'appel du samedi
2. Marquer les présences (PRESENT/ABSENT/LATE/EXCUSED)
3. Clôturer la session
4. Générer le rapport mensuel

---

### 🔒 SECRETAIRE - Administration

**Responsabilités** :
- Rédiger les rapports de réunions
- Gérer les documents
- Publier les informations

**Actions hebdomadaires** :
1. Créer le rapport de réunion
2. Ajouter les pièces jointes
3. Publier le rapport
4. Archiver les anciens rapports

---

### 🔒 COMMISSAIRE AUX COMPTES - Audit Financier

**Responsabilités** :
- Vérifier les entrées financières
- Auditer les comptes
- Générer les rapports d'audit

**Actions mensuelles** :
1. Vérifier les entrées non vérifiées
2. Rejeter les entrées incorrectes
3. Générer le rapport d'audit
4. Analyser les écarts

---

### 🔒 CHARGE LITURGIE - Formations

**Responsabilités** :
- Planifier les sessions de formation
- Gérer les inscriptions
- Évaluer les participants
- Gérer la bibliothèque de ressources

**Actions mensuelles** :
1. Créer les sessions de formation
2. Inscrire les participants
3. Marquer les présences
4. Évaluer et délivrer les certificats
5. Ajouter des ressources pédagogiques

---

### 🔒 INTENDANTS - Gestion du Matériel

**Responsabilités** :
- Gérer l'inventaire du matériel
- Planifier les tâches de nettoyage
- Suivre la maintenance
- Gérer les aubes

**Actions hebdomadaires** :
1. Créer les tâches de nettoyage
2. Assigner les servants
3. Valider les tâches terminées
4. Enregistrer les maintenances
5. Planifier le lavage des aubes

---

### 🔒 CHARGE SPORT CULTURE - Activités

**Responsabilités** :
- Organiser les journées sportives
- Planifier les sorties culturelles
- Gérer les inscriptions
- Enregistrer les résultats

**Actions mensuelles** :
1. Créer la journée sportive du 1er samedi
2. Ouvrir les inscriptions
3. Créer les équipes
4. Marquer les présences
5. Enregistrer les résultats
6. Générer le rapport

---

## 17. Notes Importantes

### Permissions Exclusives

Les permissions des responsables sont **exclusives** :
- Seul l'ECONOME peut gérer les contributions
- Seul le CENSEUR peut gérer les appels
- Seul le SECRETAIRE peut gérer les rapports
- Etc.

### Rôles Adjoints

Chaque responsable peut avoir un adjoint avec les mêmes permissions :
- ECONOME_ADJOINT
- CENSEUR_ADJOINT
- SECRETAIRE_ADJOINT
- COMMISSAIRE_AUX_COMPTES_ADJOINT
- CHARGE_LITURGIE_ADJOINT
- INTENDANT_ADJOINT
- CHARGE_SPORT_CULTURE_ADJOINT

### Traçabilité

Toutes les actions sont tracées avec :
- `created_by` : Qui a créé
- `created_at` : Quand
- `updated_at` : Dernière modification
- Champs spécifiques selon le contexte (validated_by, marked_by, etc.)

### Watermark

Tous les rapports générés incluent le logo en filigrane : `logo_servant.jpeg`

---

## 18. Endpoints par Préfixe

### `/api/v1/auth` - Authentification (7 endpoints)
- Login email/téléphone
- Inscription
- Refresh token
- Mot de passe oublié/réinitialisation

### `/api/v1/users` - Utilisateurs (12 endpoints)
- Profil personnel (5)
- Administration (7)

### `/api/v1/admin` - Administration (6 endpoints)
- Invitations (3)
- Création directe utilisateurs (3)

### `/api/v1/contributions` - Contributions (9 endpoints)
- ECONOME uniquement

### `/api/v1/attendance-sessions` - Appels (8 endpoints)
- CENSEUR uniquement

### `/api/v1/reports` - Rapports (11 endpoints)
- SECRETAIRE uniquement

### `/api/v1/financial-entries` - Finances (13 endpoints)
- COMMISSAIRE uniquement

### `/api/v1/training` - Formations (20 endpoints)
- CHARGE_LITURGIE uniquement

### `/api/v1/material` - Matériel (25 endpoints)
- INTENDANTS uniquement

### `/api/v1/sport-culture` - Sport/Culture (26 endpoints)
- CHARGE_SPORT_CULTURE uniquement

---

## Conclusion

Le backend ServantAssist propose **112 endpoints API** répartis sur **7 modules métier**, avec des permissions strictement contrôlées par rôle. Chaque responsable dispose d'un ensemble d'actions spécifiques à son domaine, tandis que tous les utilisateurs authentifiés peuvent consulter les informations pertinentes.

Le système garantit :
- ✅ Séparation claire des responsabilités
- ✅ Permissions exclusives par rôle
- ✅ Traçabilité complète de toutes les actions
- ✅ Consultation transparente pour tous
- ✅ Sécurité renforcée

---

**Document créé le** : 11 février 2026  
**Dernière mise à jour** : 11 février 2026  
**Version** : 1.0
