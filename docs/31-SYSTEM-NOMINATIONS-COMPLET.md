# 📋 Implémentation Complète des Endpoints - Contexte Nominations

**Date** : 16 février 2026  
**Version** : 1.0

---

## 🎯 Vue d'Ensemble du Système

### Concept Fondamental : Nominations Dynamiques

Dans ServantAssist, **les servants obtiennent leurs rôles via des nominations**, pas via une attribution directe de rôle utilisateur.

#### Flux :
```
Servant (rôle SERVANT)
    ↓
Nominé par ADMIN/AUMÔNIER à un poste (ex: ECONOME)
    ↓
Nomination ACTIVE
    ↓
Servant peut accéder aux endpoints ECONOME
    ↓
Nomination RÉVOQUÉE
    ↓
Servant perd les droits ECONOME
```

#### Poste Responsable Disponibles :
- `DELEGUE` : Délégué (gestion événements, décisions)
- `VICE_DELEGUE` : Vice-délégué
- `CHARGE_LITURGIE` : Responsable formation/liturgie
- `CHARGE_SPORT_CULTURE` : Responsable sport & culture
- `CENSEUR` : Censeur (discipline)
- `CENSEUR_ADJOINT` : Censeur adjoint
- `ECONOME` : Économe (finances)
- `COMMISSAIRE_AUX_COMPTES` : Commissaire (audit)
- `INTENDANT` : Intendant (logistique/matériel)

---

## 📊 Endpoints Responsables

### 1. POST `/api/v1/responsables` - Nommer un servant

**Rôles autorisés** : ADMIN, AUMÔNIER uniquement

**Description** : Nomme un SERVANT à un poste de responsable. Crée une Nomination ACTIVE.

**Body** :
```json
{
  "user_id": "uuid-du-servant",
  "poste": "ECONOME",
  "notes": "Excellent dans sa gestion"
}
```

**Validations** :
- ✅ L'utilisateur doit être un SERVANT
- ✅ Le servant ne peut avoir qu'une nomination ACTIVE à la fois
- ✅ Un seul DELEGUE peut être actif (poste unique)
- ✅ notes est optionnel, max 500 caractères

**Réponse 201** :
```json
{
  "id": "uuid-nomination",
  "user_id": "uuid-servant",
  "user": {
    "id": "uuid",
    "email": "servant@example.com",
    "first_name": "Jean",
    "last_name": "Dupont",
    "role": "SERVANT"
  },
  "poste": "ECONOME",
  "status": "ACTIVE",
  "nominated_by": "uuid-aumônier",
  "nominated_by_user": {
    "first_name": "Jean-Paul",
    "last_name": "Martin",
    "role": "AUMÔNIER"
  },
  "notes": "Excellent dans sa gestion",
  "nominated_at": "2026-02-16T10:30:00Z",
  "revoked_at": null,
  "revoked_by": null
}
```

**Erreurs** :
- `404` : Servant non trouvé
- `400` : Le servant a déjà une nomination ACTIVE
- `400` : Le poste DELEGUE est déjà pourvu
- `403` : Rôle insuffisant

---

### 2. GET `/api/v1/responsables` - Lister les responsables actuels

**Rôles autorisés** : ADMIN, AUMÔNIER uniquement

**Description** : Liste tous les servants avec une nomination ACTIVE.

**Paramètres** :
- `poste` : Filtrer par poste (optionnel) - ECONOME, CENSEUR, etc.
- `page` : Numéro de page (défaut: 1)
- `page_size` : Éléments par page (défaut: 20)

**Réponse 200** :
```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "uuid-1",
      "user": {
        "id": "uuid",
        "email": "econome@example.com",
        "first_name": "Jean",
        "last_name": "Dupont",
        "role": "SERVANT"
      },
      "poste": "ECONOME",
      "status": "ACTIVE",
      "nominated_at": "2026-01-10T14:30:00Z"
    },
    {
      "id": "uuid-2",
      "user": {
        "id": "uuid",
        "email": "censeur@example.com",
        "first_name": "Pierre",
        "last_name": "Martin",
        "role": "SERVANT"
      },
      "poste": "CENSEUR",
      "status": "ACTIVE",
      "nominated_at": "2026-01-15T09:00:00Z"
    }
  ]
}
```

**Visibilité** : ADMIN et AUMÔNIER voient tous les responsables

---

### 3. GET `/api/v1/responsables/{nomination_id}` - Détail d'une nomination

**Rôles autorisés** : ADMIN, AUMÔNIER uniquement

**Description** : Récupère les détails complets d'une nomination.

**Réponse 200** : Identique à la création (voir POST)

**Erreurs** :
- `404` : Nomination non trouvée
- `403` : Accès refusé

---

### 4. DELETE `/api/v1/responsables/{nomination_id}` - Révoquer une nomination

**Rôles autorisés** : ADMIN, AUMÔNIER uniquement

**Description** : Révoque une nomination ACTIVE (marque comme REVOQUEE).

**Body** (optionnel) :
```json
{
  "reason": "Raison de la révocation (optionnel)"
}
```

**Réponse 204** : No Content

**Effets** :
- ✅ `status` passe à `REVOQUEE`
- ✅ `revoked_at` est défini
- ✅ `revoked_by` est défini
- ✅ Le servant perd immédiatement accès aux endpoints du poste

**Erreurs** :
- `404` : Nomination non trouvée
- `400` : La nomination est déjà révoquée
- `403` : Accès refusé

---

### 5. GET `/api/v1/responsables/by-user/{user_id}` - Nomination d'un servant

**Rôles autorisés** : ADMIN, AUMÔNIER, le servant concerné (pour lui-même)

**Description** : Récupère la nomination ACTIVE actuelle d'un servant.

**Réponse 200** :
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "poste": "ECONOME",
  "status": "ACTIVE",
  "nominated_at": "2026-01-10T14:30:00Z"
}
```

**Réponse 404** : Pas de nomination ACTIVE (non nécessairement une erreur)

---

## 🔐 Système d'Autorisation Dynamique

### Pour les servants nominés :

Lorsqu'un servant accède à un endpoint (ex: `POST /api/v1/contributions`):

```
1. Vérifier l'authentification (JWT valide) ✓
2. Vérifier que l'utilisateur est un SERVANT ✓
3. Chercher la Nomination ACTIVE du servant
4. Vérifier que le poste = ECONOME
5. ✅ Autoriser l'accès
```

### Implémentation (Dependency Injection) :

```python
async def require_poste_responsable(
    expected_poste: PosteResponsable,
    current_user: User,
    session: AsyncSession
) -> User:
    """Vérifie qu'un SERVANT a une nomination ACTIVE au poste requis"""
    
    if current_user.role == UserRole.ADMIN:
        # ADMIN a accès à tout
        return current_user
    
    if current_user.role == UserRole.AUMÔNIER:
        # AUMÔNIER a accès à tout
        return current_user
    
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(403, "Vous devez être SERVANT")
    
    # Chercher la nomination ACTIVE
    nom_repo = NominationRepository(session)
    nomination = await nom_repo.get_active_by_user(current_user.id)
    
    if not nomination:
        raise HTTPException(403, "Vous n'occupez aucun poste de responsable")
    
    if nomination.poste != expected_poste:
        raise HTTPException(403, f"Vous devez être {expected_poste.value}")
    
    return current_user
```

---

## 📋 Actions par Module Responsable

### ECONOME (`poste: ECONOME`)

**Endpoints autorisés** :
- `POST /api/v1/cotisations` - Enregistrer contribution
- `GET /api/v1/cotisations` - Lister contributions
- `PATCH /api/v1/cotisations/{id}` - Modifier contribution
- `DELETE /api/v1/cotisations/{id}` - Supprimer contribution
- `GET /api/v1/cotisations/summary` - Résumés

**Condition d'accès** :
```python
@router.post("/")
async def enregistrer_contribution(
    data: ContributionCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
):
    await require_poste_responsable(PosteResponsable.ECONOME, current_user, session)
    # ... traitement
```

---

### CENSEUR (`poste: CENSEUR` ou `CENSEUR_ADJOINT`)

**Endpoints autorisés** :
- `POST /api/v1/discipline` - Créer dossier
- `GET /api/v1/discipline` - Lister dossiers
- `PATCH /api/v1/discipline/{id}` - Modifier dossier
- `DELETE /api/v1/discipline/{id}` - Supprimer dossier

**Condition d'accès** :
```python
@router.post("/")
async def creer_dossier_discipline(
    data: DisciplineCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
):
    await require_poste_responsable(
        PosteResponsable.CENSEUR, current_user, session
    )
    # ... traitement
```

**Note** : `CENSEUR_ADJOINT` a les mêmes droits que `CENSEUR`

---

### CHARGE_LITURGIE (`poste: CHARGE_LITURGIE`)

**Endpoints autorisés** :
- `POST /api/v1/training/sessions` - Créer formation
- `GET /api/v1/training/sessions` - Lister formations
- `PATCH /api/v1/training/sessions/{id}` - Modifier formation
- `DELETE /api/v1/training/sessions/{id}` - Supprimer formation

---

### CHARGE_SPORT_CULTURE (`poste: CHARGE_SPORT_CULTURE`)

**Endpoints autorisés** :
- `POST /api/v1/sport-culture` - Créer activité
- `GET /api/v1/sport-culture` - Lister activités
- `PATCH /api/v1/sport-culture/{id}` - Modifier activité

---

### ECONOME + COMMISSAIRE_AUX_COMPTES

**Endpoints partagés** :
- `GET /api/v1/financial-entries` - Lister entrées
- `POST /api/v1/financial-entries/summary` - Résumés financiers

**Endpoints COMMISSAIRE seulement** :
- Les vérifications (`/verify`)
- Les rapports d'audit

---

## 🛡️ Isolation des Données

### Par servant nominé :

Chaque servant nominé ne voit que les données pertinentes pour son poste :

```
ECONOME voit :
  ✅ Toutes les contributions
  ❌ Pas les dossiers de discipline
  
CENSEUR voit :
  ✅ Tous les dossiers de discipline
  ❌ Pas les contributions
  
Admin/Aumônier voient :
  ✅ Tout (supervision générale)
```

### Implémentation :

```python
async def list_contributions(
    current_user: User,
    session: AsyncSession
):
    # Vérifier le poste
    await require_poste_responsable(PosteResponsable.ECONOME, current_user, session)
    
    # Récupérer les contributions (accès complet pour ECONOME)
    repo = ContributionRepository(session)
    return await repo.list_all()  # ECONOME a accès à tout
```

---

## ✅ Avantages du Système

1. **Permissions dynamiques** : Les droits changent sans modifier l'utilisateur
2. **Audit complet** : Traçabilité de qui nomme/révoque
3. **Sécurité** : Les servants ne peuvent pas se nominer eux-mêmes
4. **Flexibilité** : Changement rapide de responsable
5. **Isolation** : Chaque rôle ne voit que son secteur

---

## 📝 Exemples Complets

### Cas 1 : Nommer Jean comme ECONOME

```bash
POST /api/v1/responsables
Authorization: Bearer {aumônier-token}

{
  "user_id": "uuid-jean",
  "poste": "ECONOME",
  "notes": "Excellent gestionnaire"
}

→ Jean (SERVANT) peut maintenant :
  ✅ POST /api/v1/cotisations (enregistrer contributions)
  ✅ GET /api/v1/cotisations (lister)
  ✅ PATCH /api/v1/cotisations/{id} (modifier)
  ❌ POST /api/v1/discipline (pas CENSEUR)
```

### Cas 2 : Révoquer la nomination

```bash
DELETE /api/v1/responsables/uuid-nomination
Authorization: Bearer {aumônier-token}

→ Jean (SERVANT) ne peut plus :
  ❌ POST /api/v1/cotisations (accès refusé)
```

### Cas 3 : Vérifier sa propre nomination

```bash
GET /api/v1/responsables/by-user/uuid-jean
Authorization: Bearer {jean-token}

→ Jean voit :
{
  "poste": "ECONOME",
  "status": "ACTIVE"
}
```

---

## 🔗 Table de Correspondance

| Poste | Endpoint Prefix | Repository | Service |
|-------|-----------------|------------|---------|
| ECONOME | `/api/v1/cotisations` | ContributionRepository | ContributionService |
| CENSEUR | `/api/v1/discipline` | DisciplineRepository | DisciplineService |
| CHARGE_LITURGIE | `/api/v1/training` | TrainingRepository | TrainingService |
| CHARGE_SPORT_CULTURE | `/api/v1/sport-culture` | SportCultureRepository | SportCultureService |
| COMMISSAIRE_AUX_COMPTES | `/api/v1/financial-entries` | FinancialEntryRepository | FinancialService |
| INTENDANT | `/api/v1/material` ou `/api/v1/attendance` | MaterialRepository | MaterialService |

---

## 💡 Points Clés d'Implémentation

1. **NominationRepository** : CRUD sur les nominations
2. **Dependency : require_poste_responsable()** : Vérification dynamique du poste
3. **Chaque endpoint métier** : Appelle `require_poste_responsable(expected_poste, ...)`
4. **ADMIN/AUMÔNIER** : Bypass automatique (accès complet)
5. **Servants** : Vérification stricte du poste requis
