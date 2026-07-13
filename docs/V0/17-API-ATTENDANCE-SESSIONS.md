# API Attendance Sessions - Module CENSEUR

Documentation complète de l'API de gestion des appels (Module CENSEUR).

---

## Vue d'Ensemble

Le module CENSEUR permet de gérer les appels hebdomadaires des servants, effectués chaque samedi après la messe de 06h15.

### Fonctionnalités

- Création de sessions d'appel
- Marquage de présence (PRESENT/ABSENT/LATE/EXCUSED)
- Modification des enregistrements
- Statistiques de présence par servant
- Génération de rapports
- Liste complète des servants

### Permissions

- **CENSEUR** : Accès complet (création, modification, rapports)
- **CENSEUR_ADJOINT** : Accès complet (création, modification, rapports)
- **Tous les utilisateurs authentifiés** : Consultation uniquement

---

## Endpoints

### 1. Créer une Session d'Appel

Crée une nouvelle session d'appel pour un samedi donné.

```http
POST /api/v1/attendance-sessions/
```

#### Headers

```
Authorization: Bearer <token>
Content-Type: application/json
```

#### Body

```json
{
  "session_date": "2026-02-08T00:00:00",
  "session_time": "07h30",
  "location": "Sacristie",
  "notes": "Appel du samedi 8 février"
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| session_date | datetime | Oui | Date de la session (doit être un samedi) |
| session_time | string | Non | Heure de l'appel (défaut: "07h30") |
| location | string | Non | Lieu de l'appel (défaut: "Sacristie") |
| notes | string | Non | Notes optionnelles |

#### Réponse Succès (201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "session_date": "2026-02-08T00:00:00",
  "session_time": "07h30",
  "location": "Sacristie",
  "conducted_by": "789e4567-e89b-12d3-a456-426614174000",
  "notes": "Appel du samedi 8 février",
  "created_at": "2026-02-08T07:30:00",
  "updated_at": "2026-02-08T07:30:00"
}
```

#### Erreurs

- `401 Unauthorized` : Token invalide ou manquant
- `403 Forbidden` : Utilisateur n'est pas CENSEUR/CENSEUR_ADJOINT
- `422 Validation Error` : Données invalides

---

### 2. Liste des Sessions

Récupère la liste des sessions d'appel avec pagination.

```http
GET /api/v1/attendance-sessions/
```

#### Query Parameters

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| skip | integer | 0 | Nombre d'éléments à sauter |
| limit | integer | 50 | Nombre maximum d'éléments |
| start_date | datetime | - | Filtrer à partir de cette date |
| end_date | datetime | - | Filtrer jusqu'à cette date |

#### Exemple

```http
GET /api/v1/attendance-sessions/?skip=0&limit=20&start_date=2026-02-01T00:00:00
```

#### Réponse Succès (200)

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "session_date": "2026-02-08T00:00:00",
      "session_time": "07h30",
      "location": "Sacristie",
      "conducted_by": "789e4567-e89b-12d3-a456-426614174000",
      "notes": "Appel du samedi",
      "created_at": "2026-02-08T07:30:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

---

### 3. Détail d'une Session

Récupère les détails d'une session spécifique avec tous ses enregistrements.

```http
GET /api/v1/attendance-sessions/{session_id}
```

#### Réponse Succès (200)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "session_date": "2026-02-08T00:00:00",
  "session_time": "07h30",
  "location": "Sacristie",
  "conducted_by": "789e4567-e89b-12d3-a456-426614174000",
  "notes": "Appel du samedi",
  "records": [
    {
      "id": "456e4567-e89b-12d3-a456-426614174000",
      "servant_id": "111e4567-e89b-12d3-a456-426614174000",
      "servant_name": "Jean Dupont",
      "status": "PRESENT",
      "arrival_time": "07h25",
      "notes": null,
      "recorded_by": "789e4567-e89b-12d3-a456-426614174000",
      "created_at": "2026-02-08T07:30:00"
    }
  ],
  "created_at": "2026-02-08T07:30:00",
  "updated_at": "2026-02-08T07:30:00"
}
```

#### Erreurs

- `404 Not Found` : Session introuvable

---

### 4. Marquer la Présence

Enregistre la présence d'un servant pour une session.

```http
POST /api/v1/attendance-sessions/{session_id}/records
```

#### Body

```json
{
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "status": "PRESENT",
  "arrival_time": "07h25",
  "notes": "À l'heure"
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| servant_id | UUID | Oui | ID du servant |
| status | enum | Oui | PRESENT, ABSENT, LATE, EXCUSED |
| arrival_time | string | Non | Heure d'arrivée (format: "HHhMM") |
| notes | string | Non | Notes optionnelles |

#### Réponse Succès (201)

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "status": "PRESENT",
  "arrival_time": "07h25",
  "notes": "À l'heure",
  "recorded_by": "789e4567-e89b-12d3-a456-426614174000",
  "created_at": "2026-02-08T07:30:00",
  "updated_at": "2026-02-08T07:30:00"
}
```

#### Erreurs

- `400 Bad Request` : Enregistrement déjà existant pour ce servant
- `404 Not Found` : Session ou servant introuvable

---

### 5. Modifier un Enregistrement

Modifie le statut ou les notes d'un enregistrement existant.

```http
PATCH /api/v1/attendance-sessions/records/{record_id}
```

#### Body

```json
{
  "status": "EXCUSED",
  "notes": "Justificatif médical fourni"
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| status | enum | Non | Nouveau statut |
| arrival_time | string | Non | Nouvelle heure d'arrivée |
| notes | string | Non | Nouvelles notes |

#### Réponse Succès (200)

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "status": "EXCUSED",
  "arrival_time": "07h25",
  "notes": "Justificatif médical fourni",
  "recorded_by": "789e4567-e89b-12d3-a456-426614174000",
  "created_at": "2026-02-08T07:30:00",
  "updated_at": "2026-02-08T08:00:00"
}
```

#### Erreurs

- `404 Not Found` : Enregistrement introuvable

---

### 6. Statistiques d'un Servant

Récupère les statistiques de présence d'un servant.

```http
GET /api/v1/attendance-sessions/servants/{servant_id}/stats
```

#### Query Parameters

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| start_date | datetime | - | Filtrer à partir de cette date |
| end_date | datetime | - | Filtrer jusqu'à cette date |

#### Réponse Succès (200)

```json
{
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "servant_name": "Jean Dupont",
  "total_sessions": 52,
  "present_count": 45,
  "absent_count": 3,
  "late_count": 2,
  "excused_count": 2,
  "attendance_rate": 86.54,
  "consecutive_absences": 0,
  "period": {
    "start_date": "2025-02-01T00:00:00",
    "end_date": "2026-02-01T00:00:00"
  }
}
```

#### Champs de Réponse

| Champ | Type | Description |
|-------|------|-------------|
| total_sessions | integer | Nombre total de sessions |
| present_count | integer | Nombre de présences |
| absent_count | integer | Nombre d'absences |
| late_count | integer | Nombre de retards |
| excused_count | integer | Nombre d'absences excusées |
| attendance_rate | float | Taux de présence (%) |
| consecutive_absences | integer | Nombre d'absences consécutives |

---

### 7. Générer un Rapport

Génère un rapport de présence pour une période donnée.

```http
POST /api/v1/attendance-sessions/report
```

#### Body

```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-02-28T23:59:59",
  "include_stats": true
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| start_date | datetime | Oui | Date de début |
| end_date | datetime | Oui | Date de fin |
| include_stats | boolean | Non | Inclure statistiques détaillées |

#### Réponse Succès (200)

```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-02-28T23:59:59",
  "total_sessions": 8,
  "total_servants": 25,
  "overall_attendance_rate": 88.5,
  "sessions": [
    {
      "session_date": "2026-02-08T00:00:00",
      "present": 22,
      "absent": 2,
      "late": 1,
      "excused": 0
    }
  ],
  "servant_stats": [
    {
      "servant_id": "111e4567-e89b-12d3-a456-426614174000",
      "servant_name": "Jean Dupont",
      "attendance_rate": 87.5,
      "present_count": 7,
      "absent_count": 1
    }
  ],
  "watermark_logo": "logo_servant.jpeg",
  "generated_at": "2026-02-10T10:00:00",
  "generated_by": "789e4567-e89b-12d3-a456-426614174000"
}
```

---

### 8. Liste Complète des Servants

Récupère la liste de tous les servants actifs pour l'appel.

```http
GET /api/v1/attendance-sessions/servants/list
```

#### Réponse Succès (200)

```json
[
  {
    "id": "111e4567-e89b-12d3-a456-426614174000",
    "email": "jean.dupont@test.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "phone_number": "+237600000001",
    "is_active": true
  },
  {
    "id": "222e4567-e89b-12d3-a456-426614174000",
    "email": "pierre.martin@test.com",
    "first_name": "Pierre",
    "last_name": "Martin",
    "phone_number": "+237600000002",
    "is_active": true
  }
]
```

---

## Modèles de Données

### AttendanceSession

```typescript
{
  id: UUID
  session_date: datetime
  session_time: string
  location: string
  conducted_by: UUID
  notes?: string
  created_at: datetime
  updated_at: datetime
}
```

### AttendanceRecord

```typescript
{
  id: UUID
  session_id: UUID
  servant_id: UUID
  status: "PRESENT" | "ABSENT" | "LATE" | "EXCUSED"
  arrival_time?: string
  notes?: string
  recorded_by: UUID
  created_at: datetime
  updated_at: datetime
}
```

### ServantAttendanceStats

```typescript
{
  servant_id: UUID
  servant_name: string
  total_sessions: integer
  present_count: integer
  absent_count: integer
  late_count: integer
  excused_count: integer
  attendance_rate: float
  consecutive_absences: integer
}
```

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Accès refusé (permissions insuffisantes) |
| 404 | Ressource introuvable |
| 422 | Erreur de validation |
| 429 | Trop de requêtes |
| 500 | Erreur serveur |

---

## Exemples d'Utilisation

### Workflow Complet d'un Appel

```bash
# 1. Créer une session
curl -X POST http://localhost:8000/api/v1/attendance-sessions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_date": "2026-02-08T00:00:00",
    "notes": "Appel du samedi"
  }'

# 2. Récupérer la liste des servants
curl -X GET http://localhost:8000/api/v1/attendance-sessions/servants/list \
  -H "Authorization: Bearer <token>"

# 3. Marquer présence pour chaque servant
curl -X POST http://localhost:8000/api/v1/attendance-sessions/{session_id}/records \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "111e4567-e89b-12d3-a456-426614174000",
    "status": "PRESENT",
    "arrival_time": "07h25"
  }'

# 4. Modifier un enregistrement si nécessaire
curl -X PATCH http://localhost:8000/api/v1/attendance-sessions/records/{record_id} \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "EXCUSED",
    "notes": "Justificatif fourni"
  }'

# 5. Générer un rapport mensuel
curl -X POST http://localhost:8000/api/v1/attendance-sessions/report \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-02-01T00:00:00",
    "end_date": "2026-02-28T23:59:59",
    "include_stats": true
  }'
```

---

## Bonnes Pratiques

### 1. Création de Sessions

- Créer la session le samedi matin avant l'appel
- Utiliser des notes descriptives
- Vérifier que la date est bien un samedi

### 2. Marquage de Présence

- Marquer tous les servants présents en premier
- Marquer les retards avec l'heure d'arrivée
- Ajouter des notes pour les absences

### 3. Modification d'Enregistrements

- Modifier uniquement si justificatif fourni
- Toujours ajouter une note explicative
- Ne pas modifier les sessions trop anciennes

### 4. Génération de Rapports

- Générer des rapports mensuels régulièrement
- Inclure les statistiques pour analyse
- Archiver les rapports générés

---

## Sécurité

### Authentification

Toutes les requêtes nécessitent un token JWT valide dans le header Authorization.

### Permissions

- **CENSEUR/CENSEUR_ADJOINT** : Toutes les opérations
- **Autres utilisateurs** : Lecture seule

### Validation

- Tous les UUID sont validés
- Les dates sont vérifiées
- Les statuts sont limités aux valeurs autorisées
- Protection contre injection SQL et XSS

---

## Support

Pour toute question ou problème :
- Consulter la documentation complète
- Contacter l'équipe de développement
- Vérifier les logs d'erreur

