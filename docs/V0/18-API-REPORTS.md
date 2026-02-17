# API Reports - Module SECRETAIRE

Documentation complète de l'API de gestion des rapports (Module SECRETAIRE).

---

## Vue d'Ensemble

Le module SECRETAIRE permet de gérer les rapports de réunions hebdomadaires et d'activités du groupe de servants.

### Fonctionnalités

- Création de rapports (réunions et activités)
- Modification de rapports en brouillon
- Publication de rapports
- Archivage de rapports
- Gestion des pièces jointes
- Consultation par tous les responsables

### Permissions

- **SECRETAIRE** : Accès complet (création, modification, publication, archivage)
- **SECRETAIRE_ADJOINT** : Accès complet (création, modification, publication, archivage)
- **Tous les responsables + aumônier** : Consultation des rapports publiés uniquement

---

## Endpoints

### 1. Créer un Rapport

Crée un nouveau rapport (réunion ou activité).

```http
POST /api/v1/reports/
```

#### Headers

```
Authorization: Bearer <token>
Content-Type: application/json
```

#### Body

```json
{
  "type": "REUNION",
  "title": "Réunion hebdomadaire du 8 février",
  "content": "Ordre du jour:\n1. Point sur les activités...",
  "report_date": "2026-02-08T15:00:00",
  "location": "Salle paroissiale",
  "participants": ["Jean Dupont", "Pierre Martin", "Marie Dubois"],
  "decisions": "Décision de programmer une retraite spirituelle",
  "action_items": "Action: Réserver le lieu pour la retraite"
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| type | enum | Oui | REUNION ou ACTIVITE |
| title | string | Oui | Titre du rapport (max 200 caractères) |
| content | string | Oui | Contenu du rapport |
| report_date | datetime | Oui | Date de la réunion/activité |
| location | string | Oui | Lieu (max 200 caractères) |
| participants | array[string] | Non | Liste des participants |
| decisions | string | Non | Décisions prises |
| action_items | string | Non | Actions à mener |

#### Réponse Succès (201)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "type": "REUNION",
  "title": "Réunion hebdomadaire du 8 février",
  "content": "Ordre du jour:\n1. Point sur les activités...",
  "report_date": "2026-02-08T15:00:00",
  "location": "Salle paroissiale",
  "participants": ["Jean Dupont", "Pierre Martin", "Marie Dubois"],
  "decisions": "Décision de programmer une retraite spirituelle",
  "action_items": "Action: Réserver le lieu pour la retraite",
  "status": "BROUILLON",
  "created_by": "789e4567-e89b-12d3-a456-426614174000",
  "published_at": null,
  "watermark_logo": "logo_servant.jpeg",
  "created_at": "2026-02-08T15:30:00",
  "updated_at": "2026-02-08T15:30:00"
}
```

#### Erreurs

- `401 Unauthorized` : Token invalide ou manquant
- `403 Forbidden` : Utilisateur n'est pas SECRETAIRE/SECRETAIRE_ADJOINT
- `422 Validation Error` : Données invalides

---

### 2. Liste des Rapports

Récupère la liste des rapports avec filtres et pagination.

```http
GET /api/v1/reports/
```

#### Query Parameters

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| skip | integer | 0 | Nombre d'éléments à sauter |
| limit | integer | 50 | Nombre maximum d'éléments (max 100) |
| report_type | enum | - | Filtrer par type (REUNION/ACTIVITE) |
| status | enum | - | Filtrer par statut (BROUILLON/PUBLIE/ARCHIVE) |
| start_date | datetime | - | Filtrer à partir de cette date |
| end_date | datetime | - | Filtrer jusqu'à cette date |

#### Exemple

```http
GET /api/v1/reports/?report_type=REUNION&status=PUBLIE&limit=20
```

#### Réponse Succès (200)

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "type": "REUNION",
      "title": "Réunion hebdomadaire",
      "content": "Contenu...",
      "report_date": "2026-02-08T15:00:00",
      "location": "Salle paroissiale",
      "participants": ["Jean Dupont"],
      "status": "PUBLIE",
      "created_by": "789e4567-e89b-12d3-a456-426614174000",
      "published_at": "2026-02-08T16:00:00",
      "watermark_logo": "logo_servant.jpeg",
      "created_at": "2026-02-08T15:30:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

**Note** : Les non-secrétaires ne voient que les rapports publiés.

---

### 3. Détail d'un Rapport

Récupère les détails complets d'un rapport.

```http
GET /api/v1/reports/{report_id}
```

#### Réponse Succès (200)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "type": "REUNION",
  "title": "Réunion hebdomadaire du 8 février",
  "content": "Ordre du jour:\n1. Point sur les activités...",
  "report_date": "2026-02-08T15:00:00",
  "location": "Salle paroissiale",
  "participants": ["Jean Dupont", "Pierre Martin"],
  "decisions": "Décision de programmer une retraite",
  "action_items": "Action: Réserver le lieu",
  "status": "PUBLIE",
  "created_by": "789e4567-e89b-12d3-a456-426614174000",
  "published_at": "2026-02-08T16:00:00",
  "watermark_logo": "logo_servant.jpeg",
  "created_at": "2026-02-08T15:30:00",
  "updated_at": "2026-02-08T16:00:00"
}
```

#### Erreurs

- `404 Not Found` : Rapport introuvable
- `403 Forbidden` : Accès refusé (brouillon non accessible aux non-secrétaires)

---

### 4. Modifier un Rapport

Modifie un rapport en brouillon.

```http
PATCH /api/v1/reports/{report_id}
```

#### Body

```json
{
  "title": "Titre modifié",
  "content": "Contenu modifié",
  "participants": ["Jean Dupont", "Pierre Martin", "Marie Dubois"]
}
```

#### Paramètres

Tous les champs sont optionnels. Seuls les champs fournis seront modifiés.

| Champ | Type | Description |
|-------|------|-------------|
| title | string | Nouveau titre |
| content | string | Nouveau contenu |
| report_date | datetime | Nouvelle date |
| location | string | Nouveau lieu |
| participants | array[string] | Nouvelle liste de participants |
| decisions | string | Nouvelles décisions |
| action_items | string | Nouvelles actions |

#### Réponse Succès (200)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Titre modifié",
  "content": "Contenu modifié",
  ...
}
```

#### Erreurs

- `400 Bad Request` : Rapport déjà publié (seuls les brouillons peuvent être modifiés)
- `404 Not Found` : Rapport introuvable

---

### 5. Supprimer un Rapport

Supprime un rapport en brouillon.

```http
DELETE /api/v1/reports/{report_id}
```

#### Réponse Succès (204)

Pas de contenu.

#### Erreurs

- `400 Bad Request` : Rapport déjà publié (seuls les brouillons peuvent être supprimés)
- `404 Not Found` : Rapport introuvable

---

### 6. Publier un Rapport

Publie un rapport (le rend visible à tous les responsables).

```http
POST /api/v1/reports/{report_id}/publish
```

#### Réponse Succès (200)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PUBLIE",
  "published_at": "2026-02-08T16:00:00",
  ...
}
```

#### Erreurs

- `400 Bad Request` : Rapport déjà publié
- `404 Not Found` : Rapport introuvable

---

### 7. Archiver un Rapport

Archive un rapport publié.

```http
POST /api/v1/reports/{report_id}/archive
```

#### Réponse Succès (200)

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "ARCHIVE",
  ...
}
```

#### Erreurs

- `400 Bad Request` : Seuls les rapports publiés peuvent être archivés
- `404 Not Found` : Rapport introuvable

---

### 8. Mes Rapports

Récupère les rapports créés par l'utilisateur connecté.

```http
GET /api/v1/reports/me/list
```

#### Query Parameters

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| skip | integer | 0 | Nombre d'éléments à sauter |
| limit | integer | 50 | Nombre maximum d'éléments |

#### Réponse Succès (200)

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "type": "REUNION",
      "title": "Mon rapport",
      "status": "BROUILLON",
      ...
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

---

### 9. Ajouter une Pièce Jointe

Ajoute une pièce jointe à un rapport en brouillon.

```http
POST /api/v1/reports/{report_id}/attachments
```

#### Body

```json
{
  "filename": "compte_rendu.pdf",
  "file_url": "https://storage.example.com/files/compte_rendu.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

#### Paramètres

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| filename | string | Oui | Nom du fichier (max 255 caractères) |
| file_url | string | Oui | URL du fichier |
| file_type | string | Oui | Type MIME (ex: application/pdf) |
| file_size | integer | Oui | Taille en octets |

#### Réponse Succès (201)

```json
{
  "id": "456e4567-e89b-12d3-a456-426614174000",
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "compte_rendu.pdf",
  "file_url": "https://storage.example.com/files/compte_rendu.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000,
  "uploaded_by": "789e4567-e89b-12d3-a456-426614174000",
  "created_at": "2026-02-08T15:45:00"
}
```

#### Erreurs

- `400 Bad Request` : Rapport déjà publié (pièces jointes uniquement sur brouillons)
- `404 Not Found` : Rapport introuvable

---

### 10. Liste des Pièces Jointes

Récupère les pièces jointes d'un rapport.

```http
GET /api/v1/reports/{report_id}/attachments
```

#### Réponse Succès (200)

```json
[
  {
    "id": "456e4567-e89b-12d3-a456-426614174000",
    "report_id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "compte_rendu.pdf",
    "file_url": "https://storage.example.com/files/compte_rendu.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000,
    "uploaded_by": "789e4567-e89b-12d3-a456-426614174000",
    "created_at": "2026-02-08T15:45:00"
  }
]
```

---

### 11. Supprimer une Pièce Jointe

Supprime une pièce jointe d'un rapport en brouillon.

```http
DELETE /api/v1/reports/attachments/{attachment_id}
```

#### Réponse Succès (204)

Pas de contenu.

#### Erreurs

- `400 Bad Request` : Rapport déjà publié
- `404 Not Found` : Pièce jointe introuvable

---

## Modèles de Données

### Report

```typescript
{
  id: UUID
  type: "REUNION" | "ACTIVITE"
  title: string
  content: string
  report_date: datetime
  location: string
  participants: string[]
  decisions?: string
  action_items?: string
  status: "BROUILLON" | "PUBLIE" | "ARCHIVE"
  created_by: UUID
  published_at?: datetime
  watermark_logo: string
  created_at: datetime
  updated_at: datetime
}
```

### ReportAttachment

```typescript
{
  id: UUID
  report_id: UUID
  filename: string
  file_url: string
  file_type: string
  file_size: integer
  uploaded_by: UUID
  created_at: datetime
}
```

---

## Workflow de Publication

### 1. Création (Brouillon)

```bash
POST /api/v1/reports/
{
  "type": "REUNION",
  "title": "Réunion",
  "content": "Contenu",
  ...
}
# Status: BROUILLON
```

### 2. Modification (Optionnel)

```bash
PATCH /api/v1/reports/{id}
{
  "title": "Titre modifié"
}
# Status: BROUILLON
```

### 3. Ajout de Pièces Jointes (Optionnel)

```bash
POST /api/v1/reports/{id}/attachments
{
  "filename": "document.pdf",
  ...
}
# Status: BROUILLON
```

### 4. Publication

```bash
POST /api/v1/reports/{id}/publish
# Status: PUBLIE
# Visible par tous les responsables
```

### 5. Archivage (Optionnel)

```bash
POST /api/v1/reports/{id}/archive
# Status: ARCHIVE
```

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 204 | Supprimé avec succès |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Accès refusé (permissions insuffisantes) |
| 404 | Ressource introuvable |
| 422 | Erreur de validation |
| 429 | Trop de requêtes |
| 500 | Erreur serveur |

---

## Exemples d'Utilisation

### Workflow Complet

```bash
# 1. Créer un rapport de réunion
curl -X POST http://localhost:8000/api/v1/reports/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "REUNION",
    "title": "Réunion hebdomadaire",
    "content": "Ordre du jour...",
    "report_date": "2026-02-08T15:00:00",
    "location": "Salle paroissiale",
    "participants": ["Jean", "Pierre"]
  }'

# 2. Ajouter une pièce jointe
curl -X POST http://localhost:8000/api/v1/reports/{report_id}/attachments \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "compte_rendu.pdf",
    "file_url": "https://storage.example.com/compte_rendu.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000
  }'

# 3. Publier le rapport
curl -X POST http://localhost:8000/api/v1/reports/{report_id}/publish \
  -H "Authorization: Bearer <token>"

# 4. Consulter les rapports publiés
curl -X GET http://localhost:8000/api/v1/reports/?status=PUBLIE \
  -H "Authorization: Bearer <token>"
```

---

## Bonnes Pratiques

### 1. Création de Rapports

- Créer le rapport en brouillon d'abord
- Relire et corriger avant publication
- Ajouter tous les participants
- Documenter les décisions et actions

### 2. Pièces Jointes

- Ajouter les pièces jointes avant publication
- Utiliser des noms de fichiers descriptifs
- Vérifier la taille des fichiers
- Privilégier le format PDF

### 3. Publication

- Publier rapidement après la réunion/activité
- Vérifier que tout est complet
- Ne pas publier de brouillons incomplets

### 4. Archivage

- Archiver les rapports anciens (> 1 an)
- Conserver les rapports importants publiés
- Ne pas archiver trop tôt

---

## Sécurité

### Authentification

Toutes les requêtes nécessitent un token JWT valide.

### Permissions

- **SECRETAIRE/SECRETAIRE_ADJOINT** : Toutes les opérations
- **Autres responsables** : Lecture des rapports publiés uniquement

### Validation

- Tous les UUID sont validés
- Les dates sont vérifiées
- Les types sont limités aux valeurs autorisées
- Protection contre injection SQL et XSS
- Limitation du taux de requêtes

---

## Support

Pour toute question ou problème :
- Consulter la documentation complète
- Contacter l'équipe de développement
- Vérifier les logs d'erreur

