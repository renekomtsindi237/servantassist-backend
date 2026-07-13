# Référence API

> API REST v1 — Préfixe : `/api/v1`
>
> Authentification : Bearer Token JWT (header `Authorization: Bearer <token>`)

---

## Authentification (`/api/v1/auth`)

### `POST /auth/login`
Login par email (ADMIN, AUMÔNIER uniquement).

**Format** : `application/x-www-form-urlencoded` (OAuth2)

| Champ | Type | Requis | Description |
|---|---|---|---|
| `username` | string | ✅ | Email de l'utilisateur |
| `password` | string | ✅ | Mot de passe |

**Réponse 200** :
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Erreurs** : `401` (identifiants incorrects), `403` (mauvaise méthode de login pour le rôle), `429` (trop de tentatives)

---

### `POST /auth/login/phone`
Login par téléphone (PARENT, SERVANT uniquement).

**Format** : `application/json`

```json
{
  "phone_number": "+237612345678",
  "password": "MotDePasse123"
}
```

**Réponse 200** : idem `/auth/login`

**Erreurs** : `401`, `403`, `429`

---

### `POST /auth/register`
Inscription publique (SERVANT et PARENT uniquement).

```json
{
  "email": "servant@example.com",
  "password": "MotDePasse1",
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone_number": "+237612345678",
  "role": "SERVANT",
  "invitation_code": null
}
```

| Champ | Type | Requis | Description |
|---|---|---|---|
| `email` | EmailStr | ✅ | Email unique |
| `password` | string | ✅ | 8+ chars, maj, min, chiffre |
| `first_name` | string | ✅ | Prénom |
| `last_name` | string | ✅ | Nom |
| `phone_number` | string | ⚠️ | Obligatoire pour PARENT/SERVANT |
| `role` | enum | ❌ | `SERVANT` (défaut), `PARENT` |
| `invitation_code` | string | ⚠️ | Obligatoire pour PARENT |

**Réponse 201** : `UserResponse`

**Erreurs** : `400` (email/phone déjà enregistré, code invalide), `403` (rôle non autorisé), `422` (validation)

---

### `POST /auth/refresh`
Renouveler les tokens.

```json
{ "refresh_token": "eyJhbGci..." }
```

**Réponse 200** : `Token`

---

### `POST /auth/forgot-password`
Demander un lien de réinitialisation.

```json
{ "email": "user@example.com" }
```

**Réponse 200** : `{ "message": "If the email exists, a reset link has been sent." }` (toujours 200)

---

### `POST /auth/reset-password`
Réinitialiser le mot de passe avec un token.

```json
{
  "token": "eyJhbGci...",
  "new_password": "NouveauMdp1"
}
```

**Réponse 200** : `{ "message": "Password has been reset successfully." }`

---

## Administration (`/api/v1/admin`)

> 🔒 Tous les endpoints nécessitent le rôle **ADMIN**.

### `POST /admin/invitations`
Créer un code d'invitation.

```json
{
  "role": "PARENT",
  "email": "parent@example.com",
  "phone_number": "+237612345678",
  "notes": "Parent du groupe 5A"
}
```

**Réponse 201** : `InvitationCodeResponse`

---

### `GET /admin/invitations`
Lister les invitations créées par l'admin connecté.

**Réponse 200** : `List[InvitationCodeListResponse]`

---

### `DELETE /admin/invitations/{invitation_id}`
Révoquer une invitation. Seul l'admin créateur peut révoquer.

**Réponse 204**

---

### `POST /admin/users/admin`
Créer un utilisateur ADMIN (vérifie unicité).

```json
{
  "email": "newadmin@example.com",
  "password": "SecurePass1",
  "first_name": "Admin",
  "last_name": "Deux"
}
```

---

### `POST /admin/users/aumônier`
Créer l'aumônier (vérifie unicité — un seul autorisé).

---

### `POST /admin/users/parent`
Créer un parent directement (sans code d'invitation).

---

## Utilisateurs (`/api/v1/users`)

### Self-service (tout utilisateur authentifié actif)

#### `GET /users/me`
Mon profil.

**Réponse 200** :
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "role": "SERVANT",
  "is_active": true,
  "phone_number": "+237612345678",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

#### `PATCH /users/me`
Modifier mon profil (PATCH partiel).

```json
{
  "first_name": "Jean-Pierre",
  "phone_number": "+237699887766"
}
```

**Champs modifiables** : `first_name`, `last_name`, `phone_number`

---

#### `PATCH /users/me/password`
Changer mon mot de passe.

```json
{
  "current_password": "AncienMdp1",
  "new_password": "NouveauMdp1"
}
```

**Réponse 204** (pas de body)

**Erreurs** : `400` (ancien MDP incorrect, nouveau = ancien)

---

### Administration (ADMIN uniquement) 🔒

#### `GET /users/`
Liste paginée avec filtres.

| Paramètre | Type | Description |
|---|---|---|
| `role` | enum | Filtrer par rôle (`ADMIN`, `SERVANT`, `PARENT`, `AUMÔNIER`) |
| `is_active` | bool | Filtrer par statut actif |
| `search` | string | Recherche textuelle (nom, prénom, email) |
| `page` | int | Numéro de page (défaut: 1) |
| `page_size` | int | Taille de page (défaut: 20, max: 100) |

**Réponse 200** :
```json
{
  "items": [{ "id": "...", "email": "...", ... }],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

---

#### `GET /users/{user_id}`
Détail d'un utilisateur.

#### `PATCH /users/{user_id}`
Modifier un utilisateur.

**Champs modifiables** : `first_name`, `last_name`, `email`, `phone_number`, `is_active`

#### `PATCH /users/{user_id}/deactivate`
Désactiver un compte (l'admin ne peut pas se désactiver lui-même).

#### `PATCH /users/{user_id}/activate`
Réactiver un compte.

#### `POST /users/{user_id}/reset-password`
Réinitialiser le mot de passe d'un utilisateur.

```json
{ "new_password": "NouveauMdp1" }
```

#### `DELETE /users/{user_id}`
Supprimer un utilisateur. Contraintes : ne peut pas se supprimer soi-même, ne peut pas supprimer le dernier admin.

---

## Événements (`/api/v1/activities`)

#### `GET /activities/`
Lister les événements (tout utilisateur authentifié).

| Paramètre | Type | Description |
|---|---|---|
| `start_date` | datetime | Filtrer depuis cette date |
| `end_date` | datetime | Filtrer jusqu'à cette date |

#### `GET /activities/{event_id}`
Détail d'un événement.

#### `POST /activities/` 🔒 ADMIN
Créer un événement.

```json
{
  "title": "Messe dominicale",
  "description": "10e dimanche TO",
  "start_time": "2025-03-09T09:00:00",
  "end_time": "2025-03-09T10:30:00",
  "location": "Église St-Joseph",
  "event_type": "MASS"
}
```

#### `DELETE /activities/{event_id}` 🔒 ADMIN
Supprimer un événement.

---

## Affectations (`/api/v1/assignments`)

#### `POST /assignments/` 🔒 ADMIN
Affecter un servant à un événement.

```json
{
  "event_id": "uuid",
  "user_id": "uuid",
  "role_name": "Thuriféraire"
}
```

#### `GET /assignments/me`
Mes affectations (utilisateur connecté).

#### `GET /assignments/event/{event_id}`
Affectations d'un événement.

---

## Endpoints utilitaires

#### `GET /`
```json
{ "message": "Welcome to ServantAssist API", "version": "1.0.0", "status": "operational" }
```

#### `GET /health`
```json
{ "status": "healthy", "environment": "development" }
```

---

## Codes d'erreur HTTP utilisés

| Code | Signification | Exemple |
|---|---|---|
| `200` | Succès | Login, listing |
| `201` | Créé | Inscription, création |
| `204` | Succès sans contenu | Changement MDP, suppression |
| `400` | Requête invalide | Email déjà enregistré, auto-désactivation |
| `401` | Non authentifié | Token manquant/invalide/expiré |
| `403` | Accès refusé | Rôle insuffisant, mauvaise méthode login |
| `404` | Non trouvé | Utilisateur/événement introuvable |
| `409` | Conflit | Email/téléphone déjà utilisé (update) |
| `422` | Validation échouée | Champs manquants/invalides (Pydantic) |
| `429` | Trop de requêtes | Rate limit ou brute-force |
| `500` | Erreur interne | (opaque en production avec `error_id`) |

