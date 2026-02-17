# Spécification des Modules

> Description détaillée de chaque module fonctionnel, ses règles métier, et son état d'implémentation.

---

## Module 1 : Authentification ✅ COMPLET

### Fichiers

| Couche | Fichier |
|---|---|
| Entité | `core/entities/user.py`, `core/entities/invitation.py` |
| Service | `application/services/auth_service.py` |
| API | `presentation/api/v1/auth.py`, `presentation/api/v1/admin.py` |
| Schemas | `presentation/schemas/auth.py`, `presentation/schemas/invitation.py` |
| Repository | `infrastructure/repositories/user_repository.py`, `invitation_repository.py` |
| Sécurité | `infrastructure/security/utils.py`, `infrastructure/security/brute_force.py` |

### Fonctionnalités implémentées

#### Login Email (`POST /auth/login`)
- Réservé aux rôles **ADMIN** et **AUMÔNIER**
- Format OAuth2 (`username` = email, `password`)
- Protection brute-force progressive (5/10/15/20 échecs → verrouillage 1/5/15/30 min)
- Validation Pydantic du format email
- JWT access + refresh tokens avec rôle embarqué

#### Login Téléphone (`POST /auth/login/phone`)
- Réservé aux rôles **PARENT** et **SERVANT**
- Format : `phone_number` (+indicatif + numéro) + `password`
- Mêmes protections brute-force

#### Inscription (`POST /auth/register`)
- Filtrage en amont : seuls **SERVANT** et **PARENT** autorisés
- SERVANT : auto-inscription libre
- PARENT : nécessite un `invitation_code` valide
- Validation du mot de passe : 8+ chars, majuscule, minuscule, chiffre
- Vérification unicité email et téléphone

#### Refresh Token (`POST /auth/refresh`)
- Renouvellement des tokens avec un `refresh_token` valide
- Vérifie `type: "refresh"` dans le payload JWT
- Vérifie que l'utilisateur est toujours actif

#### Mot de passe oublié (`POST /auth/forgot-password`)
- Retourne toujours 200 (anti-énumération d'emails)
- Envoie un lien de réinitialisation par email (mock en dev)

#### Réinitialisation (`POST /auth/reset-password`)
- Vérifie le token de type `reset`
- Applique le nouveau mot de passe hashé

### Règles métier d'authentification

| Règle | Implémentation |
|---|---|
| ADMIN/AUMÔNIER doivent se connecter par email | `AuthService.authenticate_user()` → 403 si mauvaise méthode |
| PARENT/SERVANT doivent se connecter par téléphone | Idem |
| Le JWT contient toujours le rôle | `SecurityUtils.create_access_token(role=...)` obligatoire |
| Cohérence JWT ↔ BDD | `auth_deps.get_current_user()` compare `token.role` vs `user.role` |
| Protection brute-force progressive | `brute_force.py` avec 4 paliers |
| ADMIN et AUMÔNIER sont uniques | `AuthService.register_user()` vérifie en BDD |

### Administration des rôles

| Endpoint | Rôle créé | Accès |
|---|---|---|
| `POST /admin/users/admin` | ADMIN | Admin uniquement (vérifie unicité) |
| `POST /admin/users/aumônier` | AUMÔNIER | Admin uniquement (vérifie unicité) |
| `POST /admin/users/parent` | PARENT | Admin uniquement (sans code invitation) |
| `POST /admin/invitations` | — | Crée un code d'invitation pour PARENT |
| `GET /admin/invitations` | — | Liste les invitations créées |
| `DELETE /admin/invitations/{id}` | — | Révoque un code d'invitation |

---

## Module 2 : Gestion des Utilisateurs ✅ COMPLET

### Fichiers

| Couche | Fichier |
|---|---|
| Service | `application/services/user_service.py` |
| API | `presentation/api/v1/users.py` |
| Schemas | `presentation/schemas/user.py` |
| Repository | `infrastructure/repositories/user_repository.py` |

### Fonctionnalités — Self-service

Tout utilisateur authentifié et actif peut :

| Endpoint | Description |
|---|---|
| `GET /users/me` | Consulter son profil complet |
| `PATCH /users/me` | Modifier son profil (first_name, last_name, phone_number) |
| `PATCH /users/me/password` | Changer son mot de passe (ancien requis) |

### Fonctionnalités — Administration

Réservé au rôle **ADMIN** :

| Endpoint | Description |
|---|---|
| `GET /users/` | Liste paginée avec filtres (role, is_active, search) |
| `GET /users/{id}` | Détail d'un utilisateur |
| `PATCH /users/{id}` | Modifier un utilisateur (email, nom, téléphone, statut) |
| `PATCH /users/{id}/deactivate` | Désactiver un compte |
| `PATCH /users/{id}/activate` | Réactiver un compte |
| `POST /users/{id}/reset-password` | Réinitialiser le mot de passe |
| `DELETE /users/{id}` | Supprimer un utilisateur |

### Règles métier

| Règle | Implémentation |
|---|---|
| L'admin ne peut pas se désactiver lui-même | `UserService.deactivate_user()` compare `user.id == admin.id` |
| L'admin ne peut pas se supprimer lui-même | `UserService.delete_user()` |
| Le dernier admin ne peut pas être supprimé | `UserRepository.count_by_role(ADMIN) <= 1` |
| Unicité email | `UserRepository.email_exists(exclude_id=)` |
| Unicité téléphone | `UserRepository.phone_exists(exclude_id=)` |
| PATCH partiel | Seuls les champs fournis sont modifiés |
| Nouveau MDP ≠ ancien | `SecurityUtils.verify_password()` sur les deux |

### Pagination

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

Paramètres : `?role=SERVANT&is_active=true&search=Jean&page=2&page_size=10`

---

## Module 3 : Événements (Activities) 🔶 PARTIEL

### Fichiers

| Couche | Fichier |
|---|---|
| Entité | `core/entities/event.py` |
| Service | `application/services/event_service.py` |
| API | `presentation/api/v1/activities.py` |
| Schemas | `presentation/schemas/event.py` |
| Repository | `infrastructure/repositories/event_repository.py` |

### État actuel

| Fonctionnalité | Statut |
|---|---|
| Lister les événements (+ filtre date) | ✅ |
| Détail d'un événement | ✅ |
| Créer un événement (admin) | ✅ |
| Supprimer un événement (admin) | ✅ |
| Modifier un événement | ❌ À implémenter |
| Traçabilité `created_by` | ❌ À ajouter à l'entité |
| Événements récurrents | ❌ V0 |
| Pagination | ❌ À ajouter |

### Types d'événements

```python
class EventType(str, Enum):
    MASS = "MASS"           # Messe
    REHEARSAL = "REHEARSAL"  # Répétition
    OTHER = "OTHER"          # Autre (fête, retraite...)
```

### Accès par rôle

| Action | ADMIN | AUMÔNIER | SERVANT | PARENT |
|---|---|---|---|---|
| Lister | ✅ | ✅ | ✅ | ✅ |
| Voir détail | ✅ | ✅ | ✅ | ✅ |
| Créer | ✅ | ❌ (V0) | ❌ | ❌ |
| Modifier | ✅ | ❌ (V0) | ❌ | ❌ |
| Supprimer | ✅ | ❌ | ❌ | ❌ |

---

## Module 4 : Affectations (Assignments) 🔶 PARTIEL

### Fichiers

| Couche | Fichier |
|---|---|
| Entité | `core/entities/assignment.py` |
| Service | `application/services/assignment_service.py` |
| API | `presentation/api/v1/assignments.py` |
| Schemas | `presentation/schemas/assignment.py` |
| Repository | `infrastructure/repositories/assignment_repository.py` |

### État actuel

| Fonctionnalité | Statut |
|---|---|
| Créer une affectation (admin) | ✅ |
| Voir mes affectations | ✅ |
| Voir les affectations d'un événement | ✅ |
| Accepter/Décliner une affectation | ❌ V0 |
| Marquer présent/absent | ❌ V0 |
| Modifier une affectation | ❌ V0 |
| Supprimer une affectation | ❌ V0 |
| Historique des présences | ❌ V0 |

### Statuts d'affectation

```python
class AssignmentStatus(str, Enum):
    PENDING = "PENDING"    # En attente de réponse
    ACCEPTED = "ACCEPTED"  # Accepté par le servant
    DECLINED = "DECLINED"  # Décliné par le servant
    PRESENT = "PRESENT"    # Présent le jour J
    ABSENT = "ABSENT"      # Absent le jour J
```

### Rôles liturgiques (exemples)

- **Cruciféraire** : porte la croix de procession
- **Thuriféraire** : porte l'encensoir
- **Naviculaire** : porte la navette à encens
- **Céroféraire** : porte les cierges
- **Porte-missel** : porte le missel
- **Acolyte** : rôle général

---

## Module 5 : Communication ❌ STUB

### État actuel

Le module n'a qu'un fichier stub (`communication.py` avec un router vide). Les services d'infrastructure existent déjà :

- `EmailService` : envoi d'emails via SMTP (mock en dev, logs)
- `WhatsAppService` : envoi via Twilio (invitations, OTP, notifications admin)

### Fonctionnalités prévues (V0)

| Fonctionnalité | Description |
|---|---|
| Notification d'affectation | Envoyer un message au servant quand il est affecté |
| Rappel d'événement | Envoyer un rappel 24h avant un événement |
| Notification de présence au parent | Informer le parent si son enfant est absent |
| Messages personnalisés admin | L'admin envoie un message à un groupe |
| Historique des notifications | Traçabilité des messages envoyés |

