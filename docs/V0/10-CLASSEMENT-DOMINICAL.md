# Classement Dominical et Solennités

## Vue d'ensemble

Le module de **Classement Dominical** permet de gérer la planification des servants de messe pour les messes dominicales et les solennités. Il offre un système complet avec traçabilité totale de toutes les modifications.

## Postes Liturgiques

### Postes Ordinaires (20 postes)

| Catégorie | Postes | Nombre |
|-----------|--------|--------|
| **Cérémoniaires** | Cérémoniaire 1, 2, 3, 4 | 4 |
| **Responsable** | Responsable | 1 |
| **Crucifère** | Crucifère | 1 |
| **Acolytes** | Acolyte 1, 2, 3, 4, 5, 6 | 6 |
| **Thuriféraire** | Thuriféraire | 1 |
| **Porte-insignes** | Porte-insignes | 1 |
| **Marmitiers Garçons** | Marmitier Garçon 1, 2, 3, 4 | 4 |
| **Marmitiers Filles** | Marmitier Fille 1, 2 | 2 |

### Postes Solennels

Pour les messes solennelles, on ajoute :
- **Céroféréraires** (porte-cierges supplémentaires)

## Horaires des Messes

### Horaires Ordinaires (5 messes)

| Heure | Langue | Jour |
|-------|--------|------|
| 06h30 | Ewondo | Dimanche |
| 08h30 | Français | Dimanche |
| 10h00 | Ewondo | Dimanche |
| 11h30 | Anglais | Dimanche |
| 17h00 | Français | Dimanche |

### Horaires Exceptionnels (personnalisables)

| Heure | Langue | Notes |
|-------|--------|-------|
| 06h30 | Ewondo | |
| 09h00 | Bilingue (Français/Ewondo) | |
| 11h30 | Anglais | |
| 17h00 | Français | |

## Permissions et Accès

### CHARGE_CLASSEMENT_DIMANCHE

Seul le **CHARGE_CLASSEMENT_DIMANCHE** (ou Admin/Aumônier) peut :
- Créer des modèles de classement
- Modifier des modèles
- Publier/archiver des modèles
- Ajouter/retirer des servants
- Supprimer des modèles

### Tous les utilisateurs authentifiés

Peuvent :
- **Consulter** les classements publiés
- **Marquer la présence** après chaque messe
- **Consulter l'historique** complet des modifications

## Traçabilité Complète

Chaque action sur un classement est tracée avec :

### Informations enregistrées
- **Qui** : Nom complet de la personne qui a fait la modification
- **Quand** : Date et heure exacte
- **Quoi** : Description détaillée de l'action
- **Où** : Adresse IP (si disponible)
- **Valeurs** : Avant et après la modification

### Types d'actions tracées
- `CREATED` : Création initiale
- `ASSIGNED` : Assignation d'un servant
- `REASSIGNED` : Réassignation à un autre servant
- `REMOVED` : Retrait d'un servant
- `PRESENCE_MARKED` : Marquage de présence
- `ABSENCE_MARKED` : Marquage d'absence
- `UPDATED` : Autre modification

## Workflow Complet

### 1. Création du Classement (CHARGE_CLASSEMENT_DIMANCHE)

#### Option A : Génération automatique avec horaires ordinaires

```bash
POST /api/v1/sunday-schedule/generate/ordinary
{
  "title": "Dimanche du temps ordinaire - 16/02/2026",
  "schedule_date": "2026-02-16T00:00:00",
  "notes": "Classement ordinaire"
}
```

Cela crée automatiquement :
- 5 messes avec les horaires ordinaires
- 20 postes vides par messe (100 postes au total)

#### Option B : Génération avec horaires exceptionnels

```bash
POST /api/v1/sunday-schedule/generate/exceptional
{
  "title": "Dimanche spécial - 16/02/2026",
  "schedule_date": "2026-02-16T00:00:00",
  "mass_times": [
    {"time": "06h30", "language": "EWONDO"},
    {"time": "09h00", "language": "BILINGUE"},
    {"time": "11h30", "language": "ANGLAIS"},
    {"time": "17h00", "language": "FRANCAIS"}
  ]
}
```

#### Option C : Création manuelle complète

```bash
POST /api/v1/sunday-schedule/
{
  "title": "Dimanche du temps ordinaire - 16/02/2026",
  "schedule_date": "2026-02-16T00:00:00",
  "mass_type": "ORDINAIRE",
  "is_exceptional": false,
  "masses": [
    {
      "mass_time": "06h30",
      "language": "EWONDO",
      "assignments": [
        {
          "position": "CEREMONIAIRE_1",
          "servant_name": "Etienne NGOUM"
        },
        // ... autres postes
      ]
    }
  ]
}
```

### 2. Remplissage du Classement

Ajouter des servants aux postes :

```bash
POST /api/v1/sunday-schedule/masses/{mass_id}/assignments
{
  "position": "ACOLYTE_1",
  "servant_id": "uuid-du-servant",  # OU
  "servant_name": "Jean DUPONT",    # Pour un servant pas encore enregistré
  "notes": "Remplaçant"
}
```

### 3. Publication

Une fois le classement rempli :

```bash
PATCH /api/v1/sunday-schedule/{template_id}/publish
```

Le classement devient visible par **tous les utilisateurs authentifiés**.

### 4. Marquage de Présence (Pendant/Après les Messes)

**Accessible à tous les utilisateurs authentifiés** :

```bash
PATCH /api/v1/sunday-schedule/assignments/{assignment_id}/presence
{
  "is_present": true  # ou false pour absence
}
```

Cette action :
- Marque la présence/absence du servant
- Enregistre qui a marqué la présence
- Enregistre l'heure exacte
- Crée une entrée dans l'historique

### 5. Consultation de l'Historique

Voir toutes les modifications :

```bash
GET /api/v1/sunday-schedule/{template_id}/history?limit=100
```

Réponse :
```json
[
  {
    "id": "uuid",
    "action": "PRESENCE_MARKED",
    "description": "Présence confirmée pour Jean DUPONT (ACOLYTE_1) à la messe de 08h30",
    "modified_by": "uuid",
    "modified_by_name": "Pierre MARTIN",
    "modified_at": "2026-02-16T08:45:00",
    "ip_address": "192.168.1.100",
    "old_value": "is_present=None",
    "new_value": "is_present=True"
  }
]
```

## Endpoints API

### Gestion (CHARGE_CLASSEMENT_DIMANCHE uniquement)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/sunday-schedule/` | Créer un modèle |
| POST | `/api/v1/sunday-schedule/generate/ordinary` | Générer avec horaires ordinaires |
| POST | `/api/v1/sunday-schedule/generate/exceptional` | Générer avec horaires exceptionnels |
| GET | `/api/v1/sunday-schedule/` | Liste paginée avec filtres |
| GET | `/api/v1/sunday-schedule/{id}` | Détail d'un modèle |
| PATCH | `/api/v1/sunday-schedule/{id}` | Modifier un modèle |
| PATCH | `/api/v1/sunday-schedule/{id}/publish` | Publier un modèle |
| PATCH | `/api/v1/sunday-schedule/{id}/archive` | Archiver un modèle |
| DELETE | `/api/v1/sunday-schedule/{id}` | Supprimer un modèle |
| PATCH | `/api/v1/sunday-schedule/masses/{id}` | Modifier une messe |
| DELETE | `/api/v1/sunday-schedule/masses/{id}` | Supprimer une messe |
| POST | `/api/v1/sunday-schedule/masses/{id}/assignments` | Ajouter une assignation |
| DELETE | `/api/v1/sunday-schedule/assignments/{id}` | Retirer une assignation |

### Consultation et Marquage (Tous les utilisateurs authentifiés)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/sunday-schedule/published` | Modèles publiés |
| GET | `/api/v1/sunday-schedule/{id}` | Détail d'un modèle |
| PATCH | `/api/v1/sunday-schedule/assignments/{id}/presence` | Marquer présence/absence |
| GET | `/api/v1/sunday-schedule/{id}/history` | Historique des modifications |

## Exemple Complet

### Scénario : Dimanche 16/02/2026

#### 1. Le CHARGE_CLASSEMENT_DIMANCHE crée le classement (Lundi 10/02)

```bash
POST /api/v1/sunday-schedule/generate/ordinary
{
  "title": "Dimanche du temps ordinaire - 16/02/2026",
  "schedule_date": "2026-02-16T00:00:00"
}
```

#### 2. Il remplit les postes (Mardi-Vendredi)

```bash
# Pour chaque messe et chaque poste
POST /api/v1/sunday-schedule/masses/{mass_id}/assignments
{
  "position": "CEREMONIAIRE_1",
  "servant_name": "Etienne NGOUM"
}
```

#### 3. Il publie le classement (Samedi 15/02)

```bash
PATCH /api/v1/sunday-schedule/{template_id}/publish
```

#### 4. Le dimanche, après chaque messe

**Messe de 06h30 terminée à 07h45** :

Un utilisateur (n'importe qui) marque les présences :

```bash
# Etienne NGOUM était présent
PATCH /api/v1/sunday-schedule/assignments/{assignment_id}/presence
{"is_present": true}

# Jean DUPONT était absent
PATCH /api/v1/sunday-schedule/assignments/{assignment_id2}/presence
{"is_present": false}
```

#### 5. Consultation de l'historique

```bash
GET /api/v1/sunday-schedule/{template_id}/history
```

Affiche :
- Création du classement par Jeanne MBIDA le 10/02 à 14h30
- Assignation de Etienne NGOUM par Jeanne MBIDA le 11/02 à 10h15
- Assignation de Jean DUPONT par Jeanne MBIDA le 11/02 à 10h16
- Publication par Jeanne MBIDA le 15/02 à 18h00
- Présence marquée pour Etienne NGOUM par Pierre MARTIN le 16/02 à 07h45
- Absence marquée pour Jean DUPONT par Pierre MARTIN le 16/02 à 07h46

## Base de Données

### Table `sunday_schedule_templates`

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| title | VARCHAR(200) | Titre du classement |
| schedule_date | DATETIME | Date du dimanche |
| mass_type | VARCHAR(20) | ORDINAIRE, SOLENNELLE, PONTIFICALE |
| is_exceptional | BOOLEAN | Horaires exceptionnels |
| status | VARCHAR(20) | DRAFT, PUBLISHED, ARCHIVED |
| notes | VARCHAR(1000) | Notes optionnelles |
| created_by | UUID | Créateur (FK users) |
| updated_by | UUID | Dernier modificateur (FK users) |
| created_at | DATETIME | Date de création |
| updated_at | DATETIME | Date de modification |

### Table `sunday_mass_slots`

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| template_id | UUID | Modèle parent (FK) |
| mass_time | VARCHAR(10) | Heure (ex: 06h30) |
| language | VARCHAR(20) | EWONDO, FRANCAIS, ANGLAIS, BILINGUE |
| notes | VARCHAR(500) | Notes optionnelles |
| created_at | DATETIME | Date de création |
| updated_at | DATETIME | Date de modification |

### Table `sunday_mass_assignments`

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| mass_slot_id | UUID | Messe (FK) |
| position | VARCHAR(30) | Poste liturgique |
| servant_id | UUID | Servant (FK users, optionnel) |
| servant_name | VARCHAR(200) | Nom libre (optionnel) |
| is_present | BOOLEAN | Présence (NULL=pas vérifié) |
| notes | VARCHAR(500) | Notes optionnelles |
| assigned_by | UUID | Qui a assigné (FK users) |
| last_modified_by | UUID | Dernière modification (FK users) |
| presence_marked_by | UUID | Qui a marqué présence (FK users) |
| presence_marked_at | DATETIME | Quand marqué |
| created_at | DATETIME | Date de création |
| updated_at | DATETIME | Date de modification |

### Table `sunday_schedule_modification_logs`

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| template_id | UUID | Modèle (FK) |
| mass_slot_id | UUID | Messe (FK, optionnel) |
| assignment_id | UUID | Assignation (FK, optionnel) |
| action | VARCHAR(30) | Type d'action |
| description | VARCHAR(500) | Description |
| modified_by | UUID | Qui (FK users) |
| modified_by_name | VARCHAR(200) | Nom complet |
| modified_at | DATETIME | Quand |
| ip_address | VARCHAR(45) | Adresse IP |
| user_agent | VARCHAR(500) | Navigateur |
| old_value | VARCHAR(1000) | Valeur avant |
| new_value | VARCHAR(1000) | Valeur après |

## Migration

Pour créer les tables dans la base de données :

```bash
# Appliquer les migrations
alembic upgrade head
```

Pour revenir en arrière :

```bash
alembic downgrade -1
```

## Sécurité et Audit

### Traçabilité

Toutes les actions sont tracées :
- ✅ Qui a fait l'action (nom complet)
- ✅ Quand (timestamp précis)
- ✅ Quoi (description détaillée)
- ✅ Où (adresse IP)
- ✅ Valeurs avant/après

### Permissions

- **Création/Modification** : Réservé au CHARGE_CLASSEMENT_DIMANCHE
- **Marquage de présence** : Tous les utilisateurs authentifiés
- **Consultation** : Tous les utilisateurs authentifiés (classements publiés uniquement)

### Intégrité

- Les modifications ne peuvent pas être supprimées de l'historique
- L'historique est immuable
- Chaque modification crée une nouvelle entrée
