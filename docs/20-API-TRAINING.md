# API Training - Module CHARGE_LITURGIE

Documentation complète de l'API de formations liturgiques (Module CHARGE_LITURGIE).

---

## Vue d'Ensemble

Le module CHARGE_LITURGIE permet de gérer les formations liturgiques des servants avec sessions, participations, matériels pédagogiques et évaluations.

### Fonctionnalités

- Planification de sessions de formation
- Inscription et gestion des participants
- Marquage de présence et évaluation
- Bibliothèque de ressources pédagogiques
- Génération de certificats
- Rapports de formation
- Statistiques par servant

### Permissions

- **CHARGE_LITURGIE / CHARGE_LITURGIE_ADJOINT** : Gestion complète
- **Tous les utilisateurs authentifiés** : Consultation et participation

---

## Endpoints Principaux

### 1. Créer une Session de Formation

```http
POST /api/v1/training/sessions
```

**Body:**
```json
{
  "title": "Formation liturgique de base",
  "description": "Introduction aux gestes liturgiques",
  "objectives": "Maîtriser les gestes de base",
  "level": "DEBUTANT",
  "date": "2026-02-15T14:00:00",
  "start_time": "14h00",
  "end_time": "16h00",
  "duration_minutes": 120,
  "location": "Salle paroissiale",
  "trainer_id": "...",
  "max_participants": 20,
  "materials_url": "https://...",
  "notes": "Prévoir des supports papier"
}
```

**Niveaux:** DEBUTANT, INTERMEDIAIRE, AVANCE, TOUS

### 2. Inscrire un Servant

```http
POST /api/v1/training/sessions/{session_id}/register
```

**Body:**
```json
{
  "servant_id": "...",
  "notes": "Première formation"
}
```

### 3. Inscrire Plusieurs Servants

```http
POST /api/v1/training/sessions/{session_id}/register-batch
```

**Body:**
```json
{
  "servant_ids": ["...", "...", "..."],
  "notes": "Inscription de groupe"
}
```

### 4. Marquer la Présence

```http
POST /api/v1/training/participations/{participation_id}/attendance
```

**Body:**
```json
{
  "status": "PRESENT",
  "notes": "Arrivé à l'heure"
}
```

**Statuts:** INSCRIT, PRESENT, ABSENT, EXCUSE

### 5. Évaluer un Participant

```http
POST /api/v1/training/participations/{participation_id}/evaluate
```

**Body:**
```json
{
  "evaluation_score": 85,
  "evaluation_comments": "Très bonne participation",
  "certificate_issued": true
}
```

### 6. Créer un Matériel Pédagogique

```http
POST /api/v1/training/materials
```

**Body:**
```json
{
  "title": "Guide du servant d'autel",
  "description": "Document PDF avec les gestes liturgiques",
  "type": "DOCUMENT",
  "file_url": "https://storage.example.com/guide.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000,
  "level": "DEBUTANT",
  "tags": ["liturgie", "gestes", "formation"],
  "is_public": true
}
```

**Types:** DOCUMENT, VIDEO, QUIZ, IMAGE, AUTRE

### 7. Statistiques d'un Servant

```http
GET /api/v1/training/servants/{servant_id}/stats?start_date=...&end_date=...
```

**Réponse:**
```json
{
  "servant_id": "...",
  "servant_name": "Jean Dupont",
  "total_sessions": 10,
  "attended_sessions": 9,
  "absent_sessions": 1,
  "attendance_rate": 90.0,
  "average_score": 85.5,
  "certificates_earned": 5,
  "last_training_date": "2026-02-15T14:00:00"
}
```

### 8. Générer un Rapport

```http
POST /api/v1/training/report
```

**Body:**
```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-12-31T23:59:59",
  "level": "DEBUTANT",
  "include_stats": true
}
```

**Réponse:**
```json
{
  "id": "...",
  "total_sessions": 25,
  "completed_sessions": 20,
  "total_participants": 150,
  "average_attendance_rate": 88.5,
  "average_evaluation_score": 82.3,
  "certificates_issued": 120,
  "top_performers": [...],
  "sessions_by_level": {
    "DEBUTANT": 10,
    "INTERMEDIAIRE": 8,
    "AVANCE": 7
  },
  "watermark_logo": "logo_servant.jpeg"
}
```

---

## Workflow de Formation

1. **Planification** : Créer une session de formation
2. **Inscription** : Inscrire les servants participants
3. **Formation** : Animer la session
4. **Présence** : Marquer la présence des participants
5. **Évaluation** : Évaluer les participants
6. **Certificat** : Délivrer les certificats
7. **Rapport** : Générer le rapport de formation

---

## Bibliothèque de Ressources

La bibliothèque contient tous les matériels pédagogiques :

- **Documents** : PDF, Word, etc.
- **Vidéos** : Démonstrations liturgiques
- **Quiz** : Évaluations
- **Images** : Schémas, photos

**Accès** :
- Matériels publics : Tous les utilisateurs authentifiés
- Matériels privés : CHARGE_LITURGIE uniquement

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 201 | Créé avec succès |
| 400 | Requête invalide (session pleine, déjà inscrit, etc.) |
| 403 | Accès refusé (non CHARGE_LITURGIE) |
| 404 | Ressource introuvable |
| 422 | Erreur de validation |

---

## Bonnes Pratiques

1. Planifier les sessions à l'avance
2. Limiter le nombre de participants si nécessaire
3. Préparer les matériels pédagogiques
4. Marquer la présence pendant la session
5. Évaluer les participants après la formation
6. Délivrer les certificats aux participants méritants
7. Générer des rapports réguliers

---

## Support

Documentation complète : `/docs/CHARGE-LITURGIE-README.md`
