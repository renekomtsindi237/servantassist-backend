# Module COMMISSAIRE_AUX_COMPTES - Guide Utilisateur

Guide complet pour l'utilisation du module d'audit financier.

---

## Vue d'Ensemble

Le module COMMISSAIRE_AUX_COMPTES permet de gérer l'audit financier du groupe de servants avec traçabilité complète de toutes les entrées d'argent.

---

## Fonctionnalités Principales

### 1. Enregistrement des Entrées Financières

Enregistrez toutes les sources de revenus :

**Types d'entrées :**
- **CONTRIBUTION** : Contributions des servants (100 FCFA/semaine ou 500 FCFA/mois)
- **DON** : Dons reçus
- **EVENEMENT** : Revenus d'événements organisés
- **COTISATION** : Cotisations spéciales
- **AUTRE** : Autres revenus

**Sources :**
- **SERVANT** : Contribution d'un servant
- **EXTERNE** : Source externe
- **EVENEMENT** : Événement organisé
- **PAROISSE** : Paroisse
- **AUTRE** : Autre source

**Exemple :**
```json
{
  "date": "2026-02-10T10:00:00",
  "amount": 5000.0,
  "category": "CONTRIBUTION",
  "source": "SERVANT",
  "reference": "CONTRIB-2026-02",
  "description": "Contributions du mois de février - 10 servants x 500 FCFA"
}
```

### 2. Vérification des Entrées

Vérifiez chaque entrée pour assurer la cohérence :

**Statuts de vérification :**
- **EN_ATTENTE** : Entrée non encore vérifiée
- **VERIFIE** : Entrée vérifiée et conforme
- **REJETE** : Entrée rejetée (anomalie détectée)

**Workflow :**
1. Consulter les entrées en attente
2. Vérifier les montants et références
3. Marquer comme VERIFIE ou REJETE
4. Ajouter des notes si nécessaire

### 3. Gestion des Écarts

Signalez et résolvez les anomalies détectées :

**Types d'écarts courants :**
- Montant incorrect
- Référence manquante
- Doublon détecté
- Incohérence avec les données ECONOME

**Exemple :**
```json
{
  "type": "Montant incorrect",
  "description": "Le montant enregistré (5000 FCFA) ne correspond pas au total des contributions individuelles (5500 FCFA)",
  "expected_amount": 5500.0,
  "actual_amount": 5000.0
}
```

### 4. Rapports d'Audit

Générez des rapports d'audit complets :

**Contenu du rapport :**
- Nombre total d'entrées
- Montant total
- Taux de vérification
- Écarts détectés
- Recommandations
- Résumés par catégorie
- Logo en filigrane

**Recommandations automatiques :**
- Taux de vérification faible
- Entrées rejetées à corriger
- Écarts non résolus
- Montants importants en attente

---

## Cas d'Usage

### Cas 1 : Audit Mensuel des Contributions

**Situation :** Fin du mois, vérification des contributions

**Actions :**
1. Récupérer les données de l'ECONOME
2. Créer une entrée pour le total du mois
3. Vérifier la cohérence avec les paiements individuels
4. Signaler les écarts si nécessaire
5. Générer le rapport mensuel

### Cas 2 : Détection d'Anomalie

**Situation :** Écart détecté entre montant attendu et réel

**Actions :**
1. Créer un écart avec description détaillée
2. Investiguer la cause
3. Corriger l'entrée si nécessaire
4. Résoudre l'écart avec notes de résolution

### Cas 3 : Rapport Annuel

**Situation :** Fin d'année, bilan financier complet

**Actions :**
1. Générer rapport pour toute l'année
2. Analyser les statistiques
3. Identifier les tendances
4. Formuler des recommandations
5. Présenter au conseil

---

## Bonnes Pratiques

### 1. Enregistrement

✅ **À FAIRE :**
- Enregistrer toutes les entrées d'argent
- Utiliser des références claires
- Descriptions détaillées
- Enregistrer rapidement

❌ **À ÉVITER :**
- Oublier des entrées
- Références vagues
- Descriptions incomplètes
- Retard d'enregistrement

### 2. Vérification

✅ **À FAIRE :**
- Vérifier régulièrement
- Croiser avec les sources
- Ajouter des notes
- Signaler les anomalies

❌ **À ÉVITER :**
- Laisser s'accumuler
- Vérifier sans croiser
- Oublier les notes
- Ignorer les anomalies

### 3. Écarts

✅ **À FAIRE :**
- Signaler immédiatement
- Description précise
- Investiguer la cause
- Résoudre rapidement

❌ **À ÉVITER :**
- Ignorer les écarts
- Descriptions vagues
- Ne pas investiguer
- Laisser non résolus

### 4. Rapports

✅ **À FAIRE :**
- Rapports mensuels
- Analyser les tendances
- Recommandations concrètes
- Archiver les rapports

❌ **À ÉVITER :**
- Rapports irréguliers
- Ignorer les tendances
- Recommandations vagues
- Ne pas archiver

---

## Collaboration avec l'ECONOME

Le COMMISSAIRE collabore étroitement avec l'ECONOME :

**Données partagées :**
- Contributions des servants
- Montants collectés
- Périodes de paiement

**Workflow collaboratif :**
1. ECONOME enregistre les contributions individuelles
2. COMMISSAIRE crée une entrée pour le total
3. COMMISSAIRE vérifie la cohérence
4. Écarts signalés et résolus ensemble

---

## Permissions

### COMMISSAIRE_AUX_COMPTES

✅ Créer des entrées financières
✅ Modifier des entrées non vérifiées
✅ Supprimer des entrées non vérifiées
✅ Vérifier des entrées
✅ Créer des écarts
✅ Résoudre des écarts
✅ Générer des rapports d'audit
✅ Consulter toutes les statistiques

---

## Traçabilité

Toutes les actions sont tracées :

- **Qui** : ID du COMMISSAIRE
- **Quand** : Date et heure
- **Quoi** : Action effectuée
- **Où** : Entrée concernée

---

## Dépannage

### Problème : Impossible de modifier une entrée

**Cause :** L'entrée est déjà vérifiée

**Solution :** Les entrées vérifiées ne peuvent pas être modifiées. Créer un écart si nécessaire.

### Problème : Écart entre ECONOME et COMMISSAIRE

**Cause :** Données non synchronisées

**Solution :** Vérifier les périodes, croiser les données, résoudre l'écart.

---

## Support

- **Documentation API** : `/docs/19-API-FINANCIAL-ENTRIES.md`
- **Email** : support@servantassist.com

---

## Changelog

### Version 1.0.0 (2026-02-10)

- ✅ Enregistrement d'entrées financières
- ✅ Vérification des entrées
- ✅ Gestion des écarts
- ✅ Rapports d'audit avec recommandations
- ✅ Statistiques financières
- ✅ Traçabilité complète
- ✅ Logo en filigrane

