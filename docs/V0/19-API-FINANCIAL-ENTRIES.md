# API Financial Entries - Module COMMISSAIRE_AUX_COMPTES

Documentation complète de l'API d'audit financier (Module COMMISSAIRE_AUX_COMPTES).

---

## Vue d'Ensemble

Le module COMMISSAIRE_AUX_COMPTES permet de gérer l'audit financier du groupe de servants avec traçabilité complète des entrées d'argent.

### Fonctionnalités

- Enregistrement d'entrées financières (contributions, dons, événements)
- Vérification des entrées (VERIFIED/PENDING/REJECTED)
- Gestion des écarts et anomalies
- Génération de rapports d'audit
- Statistiques financières détaillées

### Permissions

- **COMMISSAIRE_AUX_COMPTES** : Accès complet (création, vérification, audit)
- **ECONOME** : Collaboration (partage de données de contributions)

---

## Endpoints Principaux

### 1. Créer une Entrée Financière

```http
POST /api/v1/financial-entries/
```

**Body:**
```json
{
  "date": "2026-02-10T10:00:00",
  "amount": 5000.0,
  "category": "CONTRIBUTION",
  "source": "SERVANT",
  "reference": "CONTRIB-2026-02",
  "description": "Contributions du mois de février"
}
```

**Catégories:** CONTRIBUTION, DON, EVENEMENT, COTISATION, AUTRE

**Sources:** SERVANT, EXTERNE, EVENEMENT, PAROISSE, AUTRE

### 2. Vérifier une Entrée

```http
POST /api/v1/financial-entries/{entry_id}/verify
```

**Body:**
```json
{
  "verification_status": "VERIFIE",
  "notes": "Montant vérifié et conforme"
}
```

**Statuts:** EN_ATTENTE, VERIFIE, REJETE

### 3. Générer un Rapport d'Audit

```http
POST /api/v1/financial-entries/audit/report
```

**Body:**
```json
{
  "start_date": "2026-02-01T00:00:00",
  "end_date": "2026-02-28T23:59:59",
  "include_discrepancies": true,
  "include_recommendations": true
}
```

**Réponse:**
```json
{
  "id": "...",
  "total_entries": 45,
  "total_amount": 125000.0,
  "verified_entries": 40,
  "pending_entries": 3,
  "rejected_entries": 2,
  "discrepancies": ["Écart détecté..."],
  "recommendations": "Recommandations...",
  "summaries": [...],
  "watermark_logo": "logo_servant.jpeg"
}
```

### 4. Créer un Écart

```http
POST /api/v1/financial-entries/{entry_id}/discrepancies
```

**Body:**
```json
{
  "entry_id": "...",
  "type": "Montant incorrect",
  "description": "Le montant ne correspond pas",
  "expected_amount": 5500.0,
  "actual_amount": 5000.0
}
```

### 5. Statistiques Financières

```http
GET /api/v1/financial-entries/stats/summary?start_date=...&end_date=...
```

**Réponse:**
```json
{
  "total_amount": 125000.0,
  "total_entries": 45,
  "verified_amount": 120000.0,
  "verified_entries": 40,
  "verification_rate": 88.89,
  "average_entry_amount": 2777.78
}
```

---

## Workflow d'Audit

1. **Enregistrement** : Créer les entrées financières
2. **Vérification** : Vérifier chaque entrée
3. **Détection d'écarts** : Signaler les anomalies
4. **Résolution** : Résoudre les écarts
5. **Rapport** : Générer le rapport d'audit

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 201 | Créé avec succès |
| 400 | Requête invalide (entrée vérifiée non modifiable) |
| 403 | Accès refusé (non COMMISSAIRE) |
| 404 | Ressource introuvable |
| 422 | Erreur de validation (montant négatif, etc.) |

---

## Bonnes Pratiques

1. Enregistrer toutes les entrées d'argent
2. Vérifier régulièrement les entrées en attente
3. Signaler immédiatement les écarts détectés
4. Générer des rapports mensuels
5. Collaborer avec l'ECONOME pour les contributions

---

## Support

Documentation complète : `/docs/COMMISSAIRE-README.md`

