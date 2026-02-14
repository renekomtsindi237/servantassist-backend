# Module ECONOME - Gestion des Contributions Financières

## Vue d'Ensemble

Le module ECONOME permet de gérer les contributions mensuelles des servants de manière structurée et traçable.

### Modes de Paiement

1. **Paiement Hebdomadaire** : 100 FCFA/samedi
   - 4 paiements par mois = 400 FCFA/mois
   - Chaque paiement est enregistré avec son numéro de semaine (1-4)

2. **Paiement Mensuel** : 500 FCFA/mois
   - Paiement unique pour tout le mois
   - Montant fixe de 500 FCFA

---

## Fonctionnalités

### Pour l'ECONOME

✅ **Enregistrer les paiements**
- Cocher chaque paiement reçu
- Mode hebdomadaire ou mensuel
- Ajouter des notes

✅ **Consulter l'historique**
- Voir tous les paiements
- Filtrer par servant, mois, année
- Rechercher rapidement

✅ **Générer des rapports**
- Bilan financier complet
- Statistiques par période
- Export avec logo en filigrane

✅ **Suivre les retards**
- Identifier les servants en retard
- Taux de paiement par servant
- Alertes automatiques

### Pour les Servants

✅ **Consulter ses contributions**
- Voir son historique de paiements
- Vérifier son statut (à jour/en retard)
- Statistiques personnelles

### Pour l'Administration

✅ **Supervision complète**
- Accès à tous les paiements
- Rapports financiers
- Audit et traçabilité

---

## Architecture

```
src/
├── core/entities/contribution.py          # Entités métier
├── presentation/schemas/contribution.py   # Schémas API
├── infrastructure/repositories/
│   └── contribution_repository.py         # Accès base de données
├── application/services/
│   └── contribution_service.py            # Logique métier
└── presentation/api/v1/
    └── contributions.py                   # Endpoints API
```

---

## Utilisation

### 1. Enregistrer un Paiement Mensuel

```python
POST /api/v1/contributions/
{
  "servant_id": "uuid",
  "amount": 500.0,
  "payment_mode": "MENSUEL",
  "payment_date": "2026-02-10T10:00:00Z",
  "month": 2,
  "year": 2026,
  "notes": "Paiement février 2026"
}
```

### 2. Enregistrer un Paiement Hebdomadaire

```python
POST /api/v1/contributions/
{
  "servant_id": "uuid",
  "amount": 100.0,
  "payment_mode": "HEBDOMADAIRE",
  "payment_date": "2026-02-08T10:00:00Z",
  "month": 2,
  "year": 2026,
  "week_number": 1,
  "notes": "Semaine 1"
}
```

### 3. Consulter le Résumé Mensuel

```python
GET /api/v1/contributions/summary/2/2026
```

Retourne le résumé de tous les servants pour février 2026.

### 4. Générer un Rapport Annuel

```python
POST /api/v1/contributions/report
{
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z"
}
```

---

## Règles Métier

### Validation des Montants

- **Hebdomadaire** : Exactement 100 FCFA
- **Mensuel** : Exactement 500 FCFA
- Montants négatifs ou nuls refusés

### Validation des Dates

- Mois : 1-12
- Année : 2020-2100
- Week_number : 1-4 (uniquement pour hebdomadaire)

### Cohérence des Données

- Week_number **requis** pour paiement hebdomadaire
- Week_number **interdit** pour paiement mensuel
- Servant doit exister et avoir le rôle SERVANT

### Statuts de Paiement

- **PAYE** : Montant complet payé (≥ montant attendu)
- **EN_ATTENTE** : Paiement partiel (> 0 mais < montant attendu)
- **EN_RETARD** : Aucun paiement (= 0)

---

## Permissions

| Action | ECONOME | ADMIN | AUMÔNIER | SERVANT | Autres |
|--------|---------|-------|----------|---------|--------|
| Créer | ✅ | ✅ | ✅ | ❌ | ❌ |
| Modifier | ✅ | ✅ | ✅ | ❌ | ❌ |
| Supprimer | ✅ | ✅ | ✅ | ❌ | ❌ |
| Consulter | ✅ | ✅ | ✅ | ✅ (ses propres) | ✅ |
| Rapports | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## Traçabilité

Chaque contribution enregistre :
- **Qui** : ID et nom de l'ECONOME qui a enregistré
- **Quand** : Date et heure de création/modification
- **Quoi** : Montant, mode de paiement, mois, année
- **Pour qui** : ID et nom du servant

---

## Rapports

### Résumé Mensuel

Pour chaque servant :
- Montant attendu (400 ou 500 FCFA)
- Montant payé
- Statut (PAYE/EN_ATTENTE/EN_RETARD)
- Liste des paiements effectués

### Rapport Financier

Pour une période donnée :
- Montant total attendu
- Montant total collecté
- Taux de collecte (%)
- Nombre de servants à jour
- Nombre de servants en retard
- Détail par servant et par mois
- Logo en filigrane : `logo_servant.jpeg`

### Statistiques par Servant

- Total attendu sur la période
- Total payé
- Taux de paiement (%)
- Nombre de mois payés
- Nombre de mois en retard
- Date du dernier paiement

---

## Base de Données

### Table `contributions`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant unique |
| `servant_id` | UUID | Référence au servant |
| `amount` | Float | Montant en FCFA |
| `payment_mode` | String | HEBDOMADAIRE ou MENSUEL |
| `payment_date` | DateTime | Date du paiement |
| `month` | Integer | Mois (1-12) |
| `year` | Integer | Année |
| `week_number` | Integer | Semaine (1-4) si hebdomadaire |
| `recorded_by` | UUID | Référence à l'ECONOME |
| `notes` | Text | Notes optionnelles |
| `created_at` | DateTime | Date de création |
| `updated_at` | DateTime | Date de modification |

### Index

- `servant_id` : Recherche par servant
- `month, year` : Recherche par période
- `payment_date` : Tri chronologique
- `servant_id, month, year` : Résumé mensuel

---

## Tests

### Tests Unitaires
- Service : 15+ tests
- Repository : Couvert par les tests d'intégration

### Tests E2E
- Endpoints : 30+ tests
- Permissions : 10+ tests
- Règles métier : 10+ tests

### Tests de Performance
- Liste : < 1 seconde
- Création : < 500ms
- Résumé mensuel : < 2 secondes
- Rapport : < 3 secondes

### Tests de Sécurité
- SQL injection : ✅
- XSS : ✅
- Validation entrées : ✅
- Authentification : ✅
- Autorisation : ✅

---

## Migration

Pour créer la table :

```bash
alembic upgrade head
```

La migration `003_create_contributions_table.py` crée :
- Table `contributions`
- Index optimisés
- Contraintes de validation
- Foreign keys

---

## Exemples d'Utilisation

### Scénario 1 : Paiement Mensuel

Jean Dupont paie 500 FCFA pour février 2026.

```bash
curl -X POST "https://api.servantassist.com/api/v1/contributions/" \
  -H "Authorization: Bearer ECONOME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "jean-dupont-uuid",
    "amount": 500.0,
    "payment_mode": "MENSUEL",
    "payment_date": "2026-02-10T10:00:00Z",
    "month": 2,
    "year": 2026,
    "notes": "Paiement février 2026"
  }'
```

### Scénario 2 : Paiements Hebdomadaires

Pierre Martin paie 100 FCFA chaque samedi.

```bash
# Semaine 1
curl -X POST "https://api.servantassist.com/api/v1/contributions/" \
  -H "Authorization: Bearer ECONOME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "pierre-martin-uuid",
    "amount": 100.0,
    "payment_mode": "HEBDOMADAIRE",
    "payment_date": "2026-02-01T10:00:00Z",
    "month": 2,
    "year": 2026,
    "week_number": 1
  }'

# Semaine 2
curl -X POST "https://api.servantassist.com/api/v1/contributions/" \
  -H "Authorization: Bearer ECONOME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "servant_id": "pierre-martin-uuid",
    "amount": 100.0,
    "payment_mode": "HEBDOMADAIRE",
    "payment_date": "2026-02-08T10:00:00Z",
    "month": 2,
    "year": 2026,
    "week_number": 2
  }'

# ... Semaines 3 et 4
```

### Scénario 3 : Rapport Annuel

Générer le bilan financier de l'année 2026.

```bash
curl -X POST "https://api.servantassist.com/api/v1/contributions/report" \
  -H "Authorization: Bearer ECONOME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-01-01T00:00:00Z",
    "end_date": "2026-12-31T23:59:59Z"
  }'
```

---

## Dépannage

### Erreur : "Le montant hebdomadaire doit être 100 FCFA"

**Cause** : Montant incorrect pour un paiement hebdomadaire.

**Solution** : Utiliser exactement 100.0 pour `amount` avec `payment_mode: "HEBDOMADAIRE"`.

### Erreur : "week_number est requis pour un paiement hebdomadaire"

**Cause** : `week_number` manquant pour un paiement hebdomadaire.

**Solution** : Ajouter `week_number` (1-4) dans la requête.

### Erreur : "Servant introuvable"

**Cause** : L'UUID du servant n'existe pas.

**Solution** : Vérifier l'UUID du servant dans la base de données.

### Erreur : "Permission refusée"

**Cause** : L'utilisateur n'a pas le rôle ECONOME.

**Solution** : Utiliser un token d'ECONOME, ADMIN ou AUMÔNIER.

---

## Support

Pour toute question ou problème :
1. Consulter la documentation API : `docs/15-API-CONTRIBUTIONS.md`
2. Vérifier les tests : `tests/e2e/test_contribution_endpoints.py`
3. Contacter l'équipe de développement

---

## Changelog

### Version 1.0.0 (2026-02-10)
- ✅ Implémentation complète du module ECONOME
- ✅ Gestion des paiements hebdomadaires et mensuels
- ✅ Résumés mensuels et rapports financiers
- ✅ Traçabilité complète
- ✅ Tests complets (unitaires, e2e, performance, sécurité)
- ✅ Documentation complète
