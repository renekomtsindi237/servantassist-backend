# API - Activités Sportives et Culturelles (CHARGE_SPORT_CULTURE)

## Vue d'ensemble

Cette API permet la gestion complète des activités sportives et culturelles du groupe de servants.

**Permissions** :
- `CHARGE_SPORT_CULTURE` / `CHARGE_SPORT_CULTURE_ADJOINT` : Gestion complète
- Tous les utilisateurs authentifiés : Consultation et participation

**Base URL** : `/api/v1/sport-culture`

---

## Événements

### POST /sport-culture/events
Crée un nouvel événement sportif ou culturel.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "title": "Journée sportive mensuelle",
  "description": "Journée sportive du premier samedi du mois",
  "event_type": "JOURNEE_SPORTIVE",
  "sport_type": "FOOTBALL",
  "date": "2026-04-05T09:00:00",
  "start_time": "09h00",
  "end_time": "17h00",
  "location": "Stade municipal",
  "max_participants": 30,
  "cost": 1000.0,
  "registration_deadline": "2026-04-01T23:59:59",
  "notes": "Apporter des chaussures de sport",
  "broadcast_notification": true
}
```

**Types d'événements** :
- `JOURNEE_SPORTIVE` : Journée sportive mensuelle
- `TOURNOI` : Tournoi sportif
- `MATCH` : Match amical
- `SORTIE_CULTURELLE` : Sortie culturelle
- `SPECTACLE` : Spectacle, théâtre
- `VISITE` : Visite de musée, monument
- `AUTRE` : Autre activité

**Types de sports** :
- `FOOTBALL`, `BASKETBALL`, `VOLLEYBALL`, `HANDBALL`
- `ATHLETISME`, `NATATION`, `TENNIS`, `AUTRE`

**Statuts** :
- `PLANIFIE` : Événement planifié
- `OUVERT` : Inscriptions ouvertes
- `COMPLET` : Inscriptions complètes
- `EN_COURS` : Événement en cours
- `TERMINE` : Événement terminé
- `ANNULE` : Événement annulé

**Response** : `201 Created`

---

### GET /sport-culture/events
Liste tous les événements.

**Query Parameters** :
- `skip` (int, default=0) : Pagination
- `limit` (int, default=50, max=100) : Nombre d'éléments
- `event_type` (EventType) : Filtrer par type
- `status` (EventStatus) : Filtrer par statut
- `start_date` (datetime) : Date de début
- `end_date` (datetime) : Date de fin

**Response** : `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Journée sportive",
      "event_type": "JOURNEE_SPORTIVE",
      "status": "OUVERT",
      "participants_count": 15,
      "confirmed_count": 12,
      ...
    }
  ],
  "total": 25,
  "skip": 0,
  "limit": 50
}
```

---

### GET /sport-culture/events/{event_id}
Récupère les détails d'un événement.

**Response** : `200 OK`

---

### PATCH /sport-culture/events/{event_id}
Modifie un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** : Tous les champs sont optionnels

**Response** : `200 OK`

---

### DELETE /sport-culture/events/{event_id}
Supprime un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Response** : `204 No Content`

---

### GET /sport-culture/events/upcoming/list
Récupère les événements à venir.

**Query Parameters** :
- `limit` (int, default=10, max=50) : Nombre d'événements

**Response** : `200 OK`

---

## Participations

### POST /sport-culture/events/{event_id}/register
Inscrit un servant à un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "servant_id": "uuid",
  "notes": "Première participation"
}
```

**Response** : `201 Created`

---

### POST /sport-culture/events/{event_id}/register-batch
Inscrit plusieurs servants à un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "servant_ids": ["uuid1", "uuid2", "uuid3"],
  "notes": "Inscription par lot"
}
```

**Response** : `201 Created`

---

### GET /sport-culture/events/{event_id}/participants
Liste les participants d'un événement.

**Response** : `200 OK`

---

### POST /sport-culture/participations/{participation_id}/attendance
Marque la présence d'un participant.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "status": "PRESENT",
  "notes": "Arrivé à l'heure"
}
```

**Statuts de participation** :
- `INSCRIT` : Inscrit
- `CONFIRME` : Présence confirmée
- `PRESENT` : Présent
- `ABSENT` : Absent
- `EXCUSE` : Excusé

**Response** : `200 OK`

---

### POST /sport-culture/participations/{participation_id}/payment
Marque le paiement d'un participant.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "payment_status": true,
  "notes": "Paiement reçu"
}
```

**Response** : `200 OK`

---

### DELETE /sport-culture/participations/{participation_id}
Annule l'inscription d'un participant.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Response** : `204 No Content`

---

### GET /sport-culture/servants/{servant_id}/participations
Liste les participations d'un servant.

**Query Parameters** :
- `start_date` (datetime) : Date de début
- `end_date` (datetime) : Date de fin

**Response** : `200 OK`

---

### GET /sport-culture/servants/{servant_id}/stats
Récupère les statistiques de participation d'un servant.

**Response** : `200 OK`
```json
{
  "servant_id": "uuid",
  "total_participations": 15,
  "events_attended": 12,
  "events_missed": 3,
  "attendance_rate": 80.0,
  "total_paid": 15000.0,
  "events_by_type": {
    "JOURNEE_SPORTIVE": 8,
    "SORTIE_CULTURELLE": 4,
    "TOURNOI": 3
  }
}
```

---

## Résultats

### POST /sport-culture/events/{event_id}/results
Ajoute un résultat à un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "result_type": "VICTOIRE",
  "team_name": "Les Servants",
  "score": 5,
  "opponent_name": "Équipe adverse",
  "opponent_score": 2,
  "description": "Belle victoire de l'équipe",
  "notes": "Excellent match"
}
```

**Types de résultats** :
- `VICTOIRE` : Victoire
- `DEFAITE` : Défaite
- `NUL` : Match nul
- `CLASSEMENT` : Classement (pour les tournois)
- `PARTICIPATION` : Participation (pour les activités culturelles)

**Response** : `201 Created`

---

### GET /sport-culture/events/{event_id}/results
Récupère les résultats d'un événement.

**Response** : `200 OK`

---

### DELETE /sport-culture/results/{result_id}
Supprime un résultat.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Response** : `204 No Content`

---

## Équipes

### POST /sport-culture/events/{event_id}/teams
Crée une équipe pour un événement.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "team_name": "Équipe Alpha",
  "captain_id": "uuid",
  "members": ["uuid1", "uuid2", "uuid3"]
}
```

**Response** : `201 Created`

---

### GET /sport-culture/events/{event_id}/teams
Récupère les équipes d'un événement.

**Response** : `200 OK`

---

### PATCH /sport-culture/teams/{team_id}
Modifie une équipe.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** : Tous les champs sont optionnels

**Response** : `200 OK`

---

### DELETE /sport-culture/teams/{team_id}
Supprime une équipe.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Response** : `204 No Content`

---

## Rapports et Statistiques

### POST /sport-culture/report
Génère un rapport d'activités.

**Permissions** : CHARGE_SPORT_CULTURE uniquement

**Request Body** :
```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-12-31T23:59:59",
  "event_type": "JOURNEE_SPORTIVE"
}
```

**Response** : `200 OK`
```json
{
  "id": "uuid",
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-12-31T23:59:59",
  "total_events": 25,
  "events_by_type": {
    "JOURNEE_SPORTIVE": 12,
    "SORTIE_CULTURELLE": 8,
    "TOURNOI": 5
  },
  "total_participants": 450,
  "average_participation_rate": 85.5,
  "total_cost": 50000.0,
  "total_revenue": 45000.0,
  "events_summary": [...],
  "top_participants": [
    {
      "servant_id": "uuid",
      "servant_name": "Jean Dupont",
      "count": 20
    }
  ],
  "generated_by": "uuid",
  "watermark_logo": "logo_servant.jpeg",
  "generated_at": "2026-02-11T20:00:00"
}
```

---

### GET /sport-culture/stats
Récupère les statistiques globales.

**Response** : `200 OK`
```json
{
  "total_events": 25,
  "events_by_type": {...},
  "events_by_status": {...},
  "total_participants": 450,
  "average_participation_rate": 85.5,
  "upcoming_events": 5,
  "completed_events": 20
}
```

---

## Codes d'erreur

- `400 Bad Request` : Données invalides ou règle métier violée
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
- `registered_by` : ID de celui qui a inscrit
- `marked_by` : ID de celui qui a marqué la présence
- `recorded_by` : ID de celui qui a enregistré le résultat

---

## Notifications

Les événements avec `broadcast_notification=true` déclenchent une notification à tous les utilisateurs.

---

## Watermark

Tous les rapports incluent le logo en filigrane : `logo_servant.jpeg`

---

## Règles métier

### Inscriptions
- Un servant ne peut s'inscrire qu'une seule fois par événement
- Le nombre maximum de participants est respecté
- Les inscriptions peuvent être fermées après la deadline

### Événements
- Un événement avec participants ne peut pas être supprimé
- Les événements passés ne peuvent pas être modifiés (sauf le statut)

### Paiements
- Le paiement est optionnel (cost peut être null)
- Le paiement est tracé avec date et statut

---

## Exemples d'utilisation

### Créer une journée sportive
```bash
POST /api/v1/sport-culture/events
{
  "title": "Journée sportive d'avril",
  "description": "Football et basketball",
  "event_type": "JOURNEE_SPORTIVE",
  "sport_type": "FOOTBALL",
  "date": "2026-04-05T09:00:00",
  "start_time": "09h00",
  "end_time": "17h00",
  "location": "Stade municipal",
  "max_participants": 30,
  "cost": 1000.0,
  "broadcast_notification": true
}
```

### Inscrire plusieurs servants
```bash
POST /api/v1/sport-culture/events/{event_id}/register-batch
{
  "servant_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Ajouter un résultat
```bash
POST /api/v1/sport-culture/events/{event_id}/results
{
  "result_type": "VICTOIRE",
  "team_name": "Les Servants",
  "score": 5,
  "opponent_name": "Paroisse voisine",
  "opponent_score": 2,
  "description": "Victoire éclatante"
}
```

### Créer une équipe
```bash
POST /api/v1/sport-culture/events/{event_id}/teams
{
  "team_name": "Équipe Alpha",
  "captain_id": "uuid",
  "members": ["uuid1", "uuid2", "uuid3"]
}
```
