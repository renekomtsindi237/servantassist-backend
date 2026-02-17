# API - Gestion du Matériel (INTENDANTS)

## Vue d'ensemble

Cette API permet la gestion complète du matériel liturgique et des tâches de maintenance.

**Permissions** :
- `INTENDANT` / `INTENDANT_ADJOINT` : Gestion complète
- Tous les utilisateurs authentifiés : Consultation

**Base URL** : `/api/v1/material`

---

## Articles de Matériel

### POST /material/items
Crée un nouvel article de matériel.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "name": "Aube taille M",
  "category": "AUBE",
  "description": "Aube blanche taille M",
  "quantity": 5,
  "size": "M",
  "condition": "BON",
  "location": "Sacristie - Armoire A",
  "purchase_date": "2025-01-15T00:00:00",
  "notes": "Achat janvier 2025",
  "photo_url": "https://storage.example.com/aube_m.jpg"
}
```

**Catégories disponibles** :
- `AUBE` : Aubes des servants
- `ENCENSOIR` : Encensoirs
- `CIERGE` : Cierges et bougies
- `NAPPE` : Nappes d'autel
- `CALICE` : Calices
- `PATENE` : Patènes
- `CIBOIRE` : Ciboires
- `OSTENSOIR` : Ostensoirs
- `CROIX` : Croix processionnelles
- `AUTRE` : Autre matériel

**États disponibles** :
- `BON` : Bon état
- `A_NETTOYER` : À nettoyer
- `A_REPARER` : À réparer
- `HORS_SERVICE` : Hors service

**Response** : `201 Created`

---

### GET /material/items
Liste tous les articles de matériel.

**Query Parameters** :
- `skip` (int, default=0) : Pagination
- `limit` (int, default=50, max=100) : Nombre d'éléments
- `category` (MaterialCategory) : Filtrer par catégorie
- `condition` (MaterialCondition) : Filtrer par état
- `search` (string) : Recherche dans nom et description

**Response** : `200 OK`
```json
{
  "items": [...],
  "total": 25,
  "skip": 0,
  "limit": 50
}
```

---

### GET /material/items/{item_id}
Récupère les détails d'un article.

**Response** : `200 OK`

---

### PATCH /material/items/{item_id}
Modifie un article de matériel.

**Permissions** : INTENDANT uniquement

**Request Body** : Tous les champs sont optionnels
```json
{
  "condition": "A_NETTOYER",
  "last_maintenance_date": "2026-02-01T00:00:00",
  "next_maintenance_date": "2026-03-01T00:00:00"
}
```

**Response** : `200 OK`

---

### DELETE /material/items/{item_id}
Supprime un article de matériel.

**Permissions** : INTENDANT uniquement

**Response** : `204 No Content`

---

### GET /material/items/maintenance/needed
Liste les articles nécessitant une maintenance.

**Response** : `200 OK`

---

## Tâches de Nettoyage

### POST /material/cleaning-tasks
Crée une nouvelle tâche de nettoyage.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "title": "Nettoyage des encensoirs",
  "description": "Nettoyage complet après la messe",
  "task_type": "NETTOYAGE",
  "scheduled_date": "2026-03-01T10:00:00",
  "scheduled_time": "10h00",
  "location": "Sacristie",
  "items": ["Encensoir principal", "Encensoir secondaire"],
  "notes": "Utiliser le produit spécial"
}
```

**Types de tâches** :
- `NETTOYAGE` : Nettoyage du matériel
- `LAVAGE` : Lavage des aubes
- `REPASSAGE` : Repassage des aubes
- `REPARATION` : Réparation
- `MAINTENANCE` : Maintenance

**Statuts** :
- `PLANIFIEE` : Tâche planifiée
- `EN_COURS` : En cours
- `TERMINEE` : Terminée
- `VALIDEE` : Validée par l'intendant
- `ANNULEE` : Annulée

**Response** : `201 Created`

---

### GET /material/cleaning-tasks
Liste toutes les tâches de nettoyage.

**Query Parameters** :
- `skip`, `limit` : Pagination
- `task_type` (TaskType) : Filtrer par type
- `status` (TaskStatus) : Filtrer par statut
- `start_date` (datetime) : Date de début
- `end_date` (datetime) : Date de fin

**Response** : `200 OK`

---

### GET /material/cleaning-tasks/{task_id}
Récupère les détails d'une tâche.

**Response** : `200 OK`
```json
{
  "id": "uuid",
  "title": "Nettoyage des encensoirs",
  "status": "PLANIFIEE",
  "assigned_servants": [
    {
      "id": "uuid",
      "servant_id": "uuid",
      "servant_name": "Jean Dupont"
    }
  ],
  ...
}
```

---

### PATCH /material/cleaning-tasks/{task_id}
Modifie une tâche de nettoyage.

**Permissions** : INTENDANT uniquement

**Response** : `200 OK`

---

### POST /material/cleaning-tasks/{task_id}/complete
Marque une tâche comme terminée.

**Request Body** :
```json
{
  "photos_after": [
    "https://storage.example.com/after1.jpg",
    "https://storage.example.com/after2.jpg"
  ],
  "notes": "Nettoyage effectué avec succès"
}
```

**Response** : `200 OK`

---

### POST /material/cleaning-tasks/{task_id}/validate
Valide une tâche terminée.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "notes": "Travail bien fait"
}
```

**Response** : `200 OK`

---

### DELETE /material/cleaning-tasks/{task_id}
Supprime une tâche de nettoyage.

**Permissions** : INTENDANT uniquement

**Response** : `204 No Content`

---

## Assignations

### POST /material/cleaning-tasks/{task_id}/assign
Assigne un servant à une tâche.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "servant_id": "uuid"
}
```

**Response** : `201 Created`

---

### POST /material/cleaning-tasks/{task_id}/assign-batch
Assigne plusieurs servants à une tâche.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "servant_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response** : `201 Created`

---

### GET /material/servants/{servant_id}/assignments
Liste les assignations d'un servant.

**Query Parameters** :
- `start_date` (datetime) : Date de début
- `end_date` (datetime) : Date de fin

**Response** : `200 OK`

---

### DELETE /material/assignments/{assignment_id}
Retire une assignation.

**Permissions** : INTENDANT uniquement

**Response** : `204 No Content`

---

## Tâches d'Aubes

### POST /material/aube-tasks
Crée une nouvelle tâche de lavage/repassage d'aubes.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "title": "Lavage des aubes",
  "task_type": "LAVAGE",
  "scheduled_date": "2026-03-05T14:00:00",
  "scheduled_time": "14h00",
  "location": "Buanderie paroissiale",
  "aube_count": 15,
  "aube_sizes": ["S", "M", "L", "XL"],
  "notes": "Utiliser le programme délicat",
  "broadcast_notification": true
}
```

**Note** : Si `broadcast_notification` est `true`, tous les utilisateurs reçoivent une notification.

**Response** : `201 Created`

---

### GET /material/aube-tasks
Liste toutes les tâches d'aubes.

**Query Parameters** : Identiques aux tâches de nettoyage

**Response** : `200 OK`

---

### GET /material/aube-tasks/{task_id}
Récupère les détails d'une tâche d'aubes.

**Response** : `200 OK`

---

### PATCH /material/aube-tasks/{task_id}
Modifie une tâche d'aubes.

**Permissions** : INTENDANT uniquement

**Response** : `200 OK`

---

### POST /material/aube-tasks/{task_id}/complete
Marque une tâche d'aubes comme terminée.

**Response** : `200 OK`

---

### POST /material/aube-tasks/{task_id}/validate
Valide une tâche d'aubes terminée.

**Permissions** : INTENDANT uniquement

**Response** : `200 OK`

---

### DELETE /material/aube-tasks/{task_id}
Supprime une tâche d'aubes.

**Permissions** : INTENDANT uniquement

**Response** : `204 No Content`

---

## Historique de Maintenance

### POST /material/items/{item_id}/maintenance
Ajoute un historique de maintenance.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "maintenance_type": "LAVAGE",
  "description": "Lavage et repassage de l'aube",
  "performed_date": "2026-02-15T10:00:00",
  "cost": 500.0,
  "notes": "Maintenance effectuée avec succès"
}
```

**Response** : `201 Created`

---

### GET /material/items/{item_id}/maintenance
Récupère l'historique de maintenance d'un article.

**Response** : `200 OK`

---

## Rapports et Statistiques

### POST /material/report
Génère un rapport de gestion du matériel.

**Permissions** : INTENDANT uniquement

**Request Body** :
```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-12-31T23:59:59",
  "include_maintenance_history": true
}
```

**Response** : `200 OK`
```json
{
  "id": "uuid",
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-12-31T23:59:59",
  "total_items": 50,
  "items_by_category": {
    "AUBE": 20,
    "ENCENSOIR": 5,
    "CALICE": 10
  },
  "items_by_condition": {
    "BON": 40,
    "A_NETTOYER": 8,
    "A_REPARER": 2
  },
  "total_tasks": 25,
  "completed_tasks": 20,
  "pending_tasks": 5,
  "total_maintenance_cost": 15000.0,
  "items_needing_attention": [
    {
      "id": "uuid",
      "name": "Aube taille L",
      "condition": "A_NETTOYER",
      "reason": "À nettoyer"
    }
  ],
  "generated_by": "uuid",
  "watermark_logo": "logo_servant.jpeg",
  "generated_at": "2026-02-11T10:00:00"
}
```

---

### GET /material/stats
Récupère les statistiques globales.

**Response** : `200 OK`
```json
{
  "total_items": 50,
  "items_by_category": {...},
  "items_by_condition": {...},
  "items_needing_maintenance": 10,
  "total_tasks": 25,
  "completed_tasks": 20,
  "pending_tasks": 5,
  "completion_rate": 80.0
}
```

---

## Codes d'erreur

- `400 Bad Request` : Données invalides
- `401 Unauthorized` : Non authentifié
- `403 Forbidden` : Permissions insuffisantes
- `404 Not Found` : Ressource non trouvée
- `422 Unprocessable Entity` : Erreur de validation

---

## Traçabilité

Tous les endpoints incluent une traçabilité complète :
- `created_by` : ID de l'utilisateur créateur
- `created_at` : Date de création
- `updated_at` : Date de modification
- `validated_by` : ID du validateur (pour les tâches)
- `assigned_by` : ID de celui qui a assigné

---

## Notifications

Les tâches d'aubes avec `broadcast_notification=true` déclenchent une notification à tous les utilisateurs.

---

## Watermark

Tous les rapports incluent le logo en filigrane : `logo_servant.jpeg`
