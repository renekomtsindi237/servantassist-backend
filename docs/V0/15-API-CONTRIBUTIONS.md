## API Contributions (Module ECONOME)

Documentation complète des endpoints pour la gestion des contributions financières.

---

## Vue d'Ensemble

Le module ECONOME permet de gérer les contributions mensuelles des servants :
- **Paiement hebdomadaire** : 100 FCFA/samedi (4 samedis = 400 FCFA/mois)
- **Paiement mensuel** : 500 FCFA/mois (paiement unique)

### Permissions

| Action | ECONOME | ADMIN | AUMÔNIER | SERVANT | Autres |
|--------|---------|-------|----------|---------|--------|
| Créer contribution | ✅ | ✅ | ✅ | ❌ | ❌ |
| Modifier contribution | ✅ | ✅ | ✅ | ❌ | ❌ |
| Supprimer contribution | ✅ | ✅ | ✅ | ❌ | ❌ |
| Consulter contributions | ✅ | ✅ | ✅ | ✅ (ses propres) | ✅ |
| Générer rapports | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## Endpoints

### 1. Enregistrer un Paiement

**POST** `/api/v1/contributions/`

Enregistre un nouveau paiement de contribution.

#### Permissions
- ECONOME, ADMIN, AUMÔNIER

#### Request Body

```json
{
  "servant_id": "uuid",
  "amount": 500.0,
  "payment_mode": "MENSUEL",  // ou "HEBDOMADAIRE"
  "payment_date": "2026-02-10T10:00:00Z",
  "month": 2,
  "year": 2026,
  "week_number": null,  // Requis si HEBDOMADAIRE (1-4)
  "notes": "Paiement février 2026"
}
```

#### Validation

- `amount` : 
  - HEBDOMADAIRE : doit être 100 FCFA
  - MENSUEL : doit être 500 FCFA
- `month` : 1-12
- `year` : 2020-2100
- `week_number` : 
  - Requis si HEBDOMADAIRE (1-4)
  - Interdit si MENSUEL

#### Response (201 Created)

```json
{
  "id": "uuid",
  "servant_id": "uuid",
  "servant_name": "Jean Dupont",
  "amount": 500.0,
  "payment_mode": "MENSUEL",
  "payment_date": "2026-02-10T10:00:00Z",
  "month": 2,
  "year": 2026,
  "week_number": null,
  "recorded_by": "uuid",
  "recorded_by_name": "Marie Martin",
  "notes": "Paiement février 2026",
  "created_at": "2026-02-10T10:00:00Z",
  "updated_at": "2026-02-10T10:00:00Z"
}
```

#### Erreurs

- `404` : Servant introuvable
- `400` : L'utilisateur n'est pas un servant
- `422` : Validation échouée (montant, week_number, etc.)

---

### 2. Liste des Contributions

**GET** `/api/v1/contributions/`

Liste paginée des contributions avec filtres.

#### Permissions
- Tous les utilisateurs authentifiés

#### Query Parameters

| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `servant_id` | UUID | Filtrer par servant | - |
| `month` | int | Filtrer par mois (1-12) | - |
| `year` | int | Filtrer par année | - |
| `payment_mode` | string | HEBDOMADAIRE ou MENSUEL | - |
| `page` | int | Numéro de page | 1 |
| `page_size` | int | Taille de page (1-100) | 50 |

#### Response (200 OK)

```json
{
  "items": [
    {
      "id": "uuid",
      "servant_id": "uuid",
      "servant_name": "Jean Dupont",
      "amount": 500.0,
      "payment_mode": "MENSUEL",
      "payment_date": "2026-02-10T10:00:00Z",
      "month": 2,
      "year": 2026,
      "week_number": null,
      "recorded_by": "uuid",
      "recorded_by_name": "Marie Martin",
      "notes": "Paiement février 2026",
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-10T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "total_pages": 2
}
```

---

### 3. Détail d'une Contribution

**GET** `/api/v1/contributions/{contribution_id}`

Récupère les détails d'une contribution.

#### Permissions
- Tous les utilisateurs authentifiés

#### Response (200 OK)

```json
{
  "id": "uuid",
  "servant_id": "uuid",
  "servant_name": "Jean Dupont",
  "amount": 500.0,
  "payment_mode": "MENSUEL",
  "payment_date": "2026-02-10T10:00:00Z",
  "month": 2,
  "year": 2026,
  "week_number": null,
  "recorded_by": "uuid",
  "recorded_by_name": "Marie Martin",
  "notes": "Paiement février 2026",
  "created_at": "2026-02-10T10:00:00Z",
  "updated_at": "2026-02-10T10:00:00Z"
}
```

#### Erreurs

- `404` : Contribution introuvable

---

### 4. Modifier une Contribution

**PATCH** `/api/v1/contributions/{contribution_id}`

Modifie une contribution existante.

#### Permissions
- ECONOME, ADMIN, AUMÔNIER

#### Request Body

```json
{
  "amount": 500.0,
  "payment_date": "2026-02-10T10:00:00Z",
  "notes": "Note modifiée"
}
```

Tous les champs sont optionnels.

#### Response (200 OK)

Même format que le détail d'une contribution.

#### Erreurs

- `404` : Contribution introuvable
- `403` : Permission refusée

---

### 5. Supprimer une Contribution

**DELETE** `/api/v1/contributions/{contribution_id}`

Supprime une contribution.

#### Permissions
- ECONOME, ADMIN, AUMÔNIER

#### Response (204 No Content)

Pas de contenu.

#### Erreurs

- `404` : Contribution introuvable
- `403` : Permission refusée

---

### 6. Contributions d'un Servant

**GET** `/api/v1/contributions/servant/{servant_id}`

Récupère toutes les contributions d'un servant.

#### Permissions
- Tous les utilisateurs authentifiés

#### Query Parameters

| Paramètre | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Date de début (optionnel) |
| `end_date` | datetime | Date de fin (optionnel) |

#### Response (200 OK)

```json
[
  {
    "id": "uuid",
    "servant_id": "uuid",
    "servant_name": "Jean Dupont",
    "amount": 500.0,
    "payment_mode": "MENSUEL",
    "payment_date": "2026-02-10T10:00:00Z",
    "month": 2,
    "year": 2026,
    "week_number": null,
    "recorded_by": "uuid",
    "recorded_by_name": "Marie Martin",
    "notes": "Paiement février 2026",
    "created_at": "2026-02-10T10:00:00Z",
    "updated_at": "2026-02-10T10:00:00Z"
  }
]
```

---

### 7. Statistiques d'un Servant

**GET** `/api/v1/contributions/servant/{servant_id}/stats`

Calcule les statistiques de contribution d'un servant.

#### Permissions
- Tous les utilisateurs authentifiés

#### Query Parameters

| Paramètre | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Date de début (requis) |
| `end_date` | datetime | Date de fin (requis) |

#### Response (200 OK)

```json
{
  "servant_id": "uuid",
  "servant_name": "Jean Dupont",
  "total_expected": 6000.0,
  "total_paid": 5500.0,
  "payment_rate": 91.67,
  "months_paid": 11,
  "months_late": 1,
  "last_payment_date": "2026-11-10T10:00:00Z"
}
```

---

### 8. Résumé Mensuel

**GET** `/api/v1/contributions/summary/{month}/{year}`

Génère le résumé des contributions pour un mois donné.

#### Permissions
- Tous les utilisateurs authentifiés

#### Path Parameters

| Paramètre | Type | Description |
|-----------|------|-------------|
| `month` | int | Mois (1-12) |
| `year` | int | Année |

#### Response (200 OK)

```json
[
  {
    "servant_id": "uuid",
    "servant_name": "Jean Dupont",
    "month": 2,
    "year": 2026,
    "expected_amount": 500.0,
    "paid_amount": 500.0,
    "payment_mode": "MENSUEL",
    "status": "PAYE",
    "payments": [
      {
        "id": "uuid",
        "servant_id": "uuid",
        "servant_name": "Jean Dupont",
        "amount": 500.0,
        "payment_mode": "MENSUEL",
        "payment_date": "2026-02-10T10:00:00Z",
        "month": 2,
        "year": 2026,
        "week_number": null,
        "recorded_by": "uuid",
        "recorded_by_name": "Marie Martin",
        "notes": "Paiement février 2026",
        "created_at": "2026-02-10T10:00:00Z",
        "updated_at": "2026-02-10T10:00:00Z"
      }
    ]
  }
]
```

#### Statuts Possibles

- `PAYE` : Montant complet payé
- `EN_ATTENTE` : Paiement partiel
- `EN_RETARD` : Aucun paiement

---

### 9. Générer un Rapport Financier

**POST** `/api/v1/contributions/report`

Génère un rapport financier complet pour une période.

#### Permissions
- ECONOME, ADMIN, AUMÔNIER

#### Request Body

```json
{
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z",
  "servant_ids": ["uuid1", "uuid2"]  // Optionnel : filtrer par servants
}
```

#### Response (200 OK)

```json
{
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z",
  "total_expected": 120000.0,
  "total_collected": 96000.0,
  "collection_rate": 80.0,
  "servants_paid": 16,
  "servants_late": 4,
  "contributions": [
    {
      "servant_id": "uuid",
      "servant_name": "Jean Dupont",
      "month": 2,
      "year": 2026,
      "expected_amount": 500.0,
      "paid_amount": 500.0,
      "payment_mode": "MENSUEL",
      "status": "PAYE",
      "payments": [...]
    }
  ],
  "generated_by": "uuid",
  "generated_by_name": "Marie Martin",
  "generated_at": "2026-02-10T10:00:00Z",
  "watermark_logo": "logo_servant.jpeg"
}
```

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| `200` | Succès |
| `201` | Créé avec succès |
| `204` | Supprimé avec succès |
| `400` | Requête invalide |
| `401` | Non authentifié |
| `403` | Permission refusée |
| `404` | Ressource introuvable |
| `422` | Validation échouée |
| `429` | Trop de requêtes (rate limiting) |
| `500` | Erreur serveur |

---

## Exemples d'Utilisation

### Exemple 1 : Enregistrer un Paiement Mensuel

```bash
curl -X POST "https://api.servantassist.com/api/v1/contributions/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": 500.0,
    "payment_mode": "MENSUEL",
    "payment_date": "2026-02-10T10:00:00Z",
    "month": 2,
    "year": 2026,
    "notes": "Paiement février 2026"
  }'
```

### Exemple 2 : Enregistrer un Paiement Hebdomadaire

```bash
curl -X POST "https://api.servantassist.com/api/v1/contributions/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": 100.0,
    "payment_mode": "HEBDOMADAIRE",
    "payment_date": "2026-02-08T10:00:00Z",
    "month": 2,
    "year": 2026,
    "week_number": 1,
    "notes": "Semaine 1"
  }'
```

### Exemple 3 : Générer un Rapport Annuel

```bash
curl -X POST "https://api.servantassist.com/api/v1/contributions/report" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-01-01T00:00:00Z",
    "end_date": "2026-12-31T23:59:59Z"
  }'
```

---

## Notes Importantes

1. **Traçabilité** : Chaque contribution enregistre qui l'a créée et quand
2. **Logo en Filigrane** : Tous les rapports incluent `logo_servant.jpeg`
3. **Validation Stricte** : Les montants et modes de paiement sont validés
4. **Permissions** : Seul l'ECONOME peut créer/modifier les contributions
5. **Consultation** : Tous les utilisateurs peuvent consulter les contributions
