# Classement Hebdomadaire des Messes

## Vue d'ensemble

Le module de **Classement Hebdomadaire** permet de gérer la planification des servants de messe pour les messes en semaine. Il offre un système de modèles (templates) qui peuvent être créés, remplis et publiés pour être visibles par tous les membres.

## Horaires des Messes en Semaine

Le système gère automatiquement les horaires fixes suivants :

| Horaire | Lundi | Mardi | Mercredi | Jeudi | Vendredi | Samedi |
|---------|-------|-------|----------|-------|----------|--------|
| **Matin (6h15)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Midi (12h00)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Soir (18h00)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |

**Total : 16 créneaux par semaine**
- 6 créneaux du matin (Lundi-Samedi)
- 5 créneaux du midi (Lundi-Vendredi)
- 5 créneaux du soir (Lundi-Vendredi)

## Fonctionnalités

### 1. Création d'un Modèle

Le responsable du classement (Aumônier ou Admin) peut créer un nouveau modèle de deux façons :

#### Option A : Modèle vierge (à remplir manuellement)

```bash
POST /api/v1/weekly-schedule/
{
  "title": "Semaine du 10/02 au 16/02/2026",
  "start_date": "2026-02-10T00:00:00",
  "end_date": "2026-02-16T23:59:59",
  "notes": "Classement de la semaine",
  "slots": []
}
```

#### Option B : Modèle pré-rempli avec tous les créneaux

Utiliser le script de génération automatique :

```bash
python scripts/generate_weekly_template.py \
  --start-date "2026-02-10" \
  --title "Semaine du 10/02 au 16/02/2026" \
  --output template.json
```

Puis créer le modèle via l'API :

```bash
curl -X POST http://localhost:8000/api/v1/weekly-schedule/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @template.json
```

### 2. Remplissage du Modèle

Une fois le modèle créé, le responsable peut assigner des servants à chaque créneau :

```bash
PATCH /api/v1/weekly-schedule/slots/{slot_id}
{
  "servant_id": "uuid-du-servant",  # OU
  "servant_name": "Jean DUPONT",    # Pour un servant pas encore dans le système
  "notes": "Remplaçant de Pierre"
}
```

**Deux options pour assigner un servant :**
- `servant_id` : Utiliser l'ID d'un servant déjà enregistré dans le système
- `servant_name` : Entrer un nom libre pour un servant pas encore enregistré

### 3. Publication du Modèle

Une fois le modèle rempli, le responsable peut le publier pour le rendre visible par tous :

```bash
PATCH /api/v1/weekly-schedule/{template_id}/publish
```

**Statuts disponibles :**
- `DRAFT` : Brouillon (visible uniquement par Admin/Aumônier)
- `PUBLISHED` : Publié (visible par tous les utilisateurs authentifiés)
- `ARCHIVED` : Archivé (pour l'historique)

### 4. Consultation par les Utilisateurs

Tous les utilisateurs authentifiés peuvent consulter les modèles publiés :

```bash
GET /api/v1/weekly-schedule/published
```

Réponse :
```json
[
  {
    "id": "uuid",
    "title": "Semaine du 10/02 au 16/02/2026",
    "start_date": "2026-02-10T00:00:00",
    "end_date": "2026-02-16T23:59:59",
    "status": "PUBLISHED",
    "total_slots": 16,
    "filled_slots": 14,
    "creator_first_name": "Père",
    "creator_last_name": "Martin",
    "created_at": "2026-02-08T10:00:00"
  }
]
```

### 5. Détail d'un Modèle

Pour voir tous les créneaux d'un modèle :

```bash
GET /api/v1/weekly-schedule/{template_id}
```

Réponse :
```json
{
  "id": "uuid",
  "title": "Semaine du 10/02 au 16/02/2026",
  "start_date": "2026-02-10T00:00:00",
  "end_date": "2026-02-16T23:59:59",
  "status": "PUBLISHED",
  "slots": [
    {
      "id": "uuid",
      "day": "LUNDI",
      "mass_time": "MATIN",
      "servant_id": "uuid",
      "servant_first_name": "Jean",
      "servant_last_name": "DUPONT",
      "notes": null
    },
    {
      "id": "uuid",
      "day": "LUNDI",
      "mass_time": "MIDI",
      "servant_id": null,
      "servant_name": "Pierre MARTIN",
      "notes": "Nouveau servant"
    }
  ]
}
```

## Workflow Complet

### Pour le Responsable du Classement (Aumônier/Admin)

1. **Créer un modèle vierge**
   ```bash
   python scripts/generate_weekly_template.py --start-date "2026-02-10" --output template.json
   ```

2. **Uploader le modèle**
   ```bash
   POST /api/v1/weekly-schedule/ @template.json
   ```

3. **Remplir les créneaux** (assigner les servants)
   ```bash
   PATCH /api/v1/weekly-schedule/slots/{slot_id}
   ```

4. **Publier le modèle**
   ```bash
   PATCH /api/v1/weekly-schedule/{template_id}/publish
   ```

### Pour les Utilisateurs (Servants, Parents, etc.)

1. **Consulter les classements publiés**
   ```bash
   GET /api/v1/weekly-schedule/published
   ```

2. **Voir le détail d'un classement**
   ```bash
   GET /api/v1/weekly-schedule/{template_id}
   ```

## Endpoints API

### Gestion (Admin / Aumônier uniquement)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/weekly-schedule/` | Créer un modèle |
| GET | `/api/v1/weekly-schedule/` | Liste paginée avec filtres |
| GET | `/api/v1/weekly-schedule/{id}` | Détail d'un modèle |
| PATCH | `/api/v1/weekly-schedule/{id}` | Modifier un modèle |
| PATCH | `/api/v1/weekly-schedule/{id}/publish` | Publier un modèle |
| PATCH | `/api/v1/weekly-schedule/{id}/archive` | Archiver un modèle |
| DELETE | `/api/v1/weekly-schedule/{id}` | Supprimer un modèle |
| PATCH | `/api/v1/weekly-schedule/slots/{id}` | Modifier un créneau |
| DELETE | `/api/v1/weekly-schedule/slots/{id}` | Supprimer un créneau |

### Consultation (Tous les utilisateurs authentifiés)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/weekly-schedule/published` | Modèles publiés |
| GET | `/api/v1/weekly-schedule/{id}` | Détail d'un modèle |

## Exemples d'Utilisation

### Exemple 1 : Créer un classement complet

```python
import requests

# 1. Générer le template
template = {
    "title": "Semaine du 10/02 au 16/02/2026",
    "start_date": "2026-02-10T00:00:00",
    "end_date": "2026-02-16T23:59:59",
    "slots": [
        {"day": "LUNDI", "mass_time": "MATIN", "servant_name": "Jean DUPONT"},
        {"day": "LUNDI", "mass_time": "MIDI", "servant_name": "Pierre MARTIN"},
        # ... tous les autres créneaux
    ]
}

# 2. Créer le modèle
response = requests.post(
    "http://localhost:8000/api/v1/weekly-schedule/",
    json=template,
    headers={"Authorization": f"Bearer {token}"}
)
template_id = response.json()["id"]

# 3. Publier
requests.patch(
    f"http://localhost:8000/api/v1/weekly-schedule/{template_id}/publish",
    headers={"Authorization": f"Bearer {token}"}
)
```

### Exemple 2 : Consulter les classements publiés

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/weekly-schedule/published",
    headers={"Authorization": f"Bearer {token}"}
)

for schedule in response.json():
    print(f"{schedule['title']}: {schedule['filled_slots']}/{schedule['total_slots']} créneaux remplis")
```

## Intégration avec le Frontend

Le frontend peut afficher le classement sous forme de tableau similaire au modèle papier :

```
┌─────────────────────────────────────────────────────────────────┐
│         CLASSEMENT HEBDOMADAIRE DU 10/02 AU 16/02/2026         │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│  LUNDI   │  MARDI   │ MERCREDI │  JEUDI   │ VENDREDI │  SAMEDI  │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 6h15     │ 6h15     │ 6h15     │ 6h15     │ 6h15     │ 6h15     │
│ Jean     │ Pierre   │ André    │ Paul     │ Nicolas  │ Adrien   │
│ DUPONT   │ MARTIN   │ NSAMBA   │ EYENGA   │ ATANGANA │ MANGA    │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 12h00    │ 12h00    │ 12h00    │ 12h00    │ 12h00    │          │
│ Albert   │ David    │ Eric     │ Thierry  │ Nathanel │          │
│ LOMO     │ MONGO    │ NZAMBA   │ EYENGA   │ NANGA    │          │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 18h00    │ 18h00    │ 18h00    │ 18h00    │ 18h00    │          │
│ Israël   │ Maud     │ Hermann  │ Ingrid   │ Hayael   │          │
│ ABAH     │ ODONGO   │ MUKENDI  │ NSAMBA   │ LONGA    │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

## Sécurité et Permissions

- **Création/Modification/Suppression** : Réservé aux rôles `ADMIN` et `AUMONIER`
- **Publication** : Réservé aux rôles `ADMIN` et `AUMONIER`
- **Consultation des brouillons** : Réservé aux rôles `ADMIN` et `AUMONIER`
- **Consultation des modèles publiés** : Tous les utilisateurs authentifiés

## Base de Données

### Table `weekly_schedule_templates`

Stocke les modèles de classement hebdomadaire.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| title | VARCHAR(200) | Titre du classement |
| start_date | DATETIME | Date de début |
| end_date | DATETIME | Date de fin |
| status | VARCHAR(20) | DRAFT, PUBLISHED, ARCHIVED |
| notes | VARCHAR(1000) | Notes optionnelles |
| created_by | UUID | Créateur (FK users) |
| updated_by | UUID | Dernier modificateur (FK users) |
| created_at | DATETIME | Date de création |
| updated_at | DATETIME | Date de modification |

### Table `weekly_schedule_slots`

Stocke les créneaux de messe individuels.

| Colonne | Type | Description |
|---------|------|-------------|
| id | UUID | Identifiant unique |
| template_id | UUID | Modèle parent (FK) |
| day | VARCHAR(20) | LUNDI, MARDI, etc. |
| mass_time | VARCHAR(20) | MATIN, MIDI, SOIR |
| servant_id | UUID | Servant assigné (FK users, optionnel) |
| servant_name | VARCHAR(200) | Nom libre (optionnel) |
| notes | VARCHAR(500) | Notes optionnelles |
| created_at | DATETIME | Date de création |
| updated_at | DATETIME | Date de modification |

## Migration

Pour créer les tables dans la base de données :

```bash
# Appliquer la migration
alembic upgrade head
```

Pour revenir en arrière :

```bash
alembic downgrade -1
```
