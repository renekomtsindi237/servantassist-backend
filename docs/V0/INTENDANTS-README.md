# Guide Utilisateur - Module INTENDANTS

## Vue d'ensemble

Le module INTENDANTS permet la gestion complète du matériel liturgique, des tâches de nettoyage et de maintenance.

**Responsables** : INTENDANT et INTENDANT_ADJOINT

---

## Fonctionnalités principales

### 1. Gestion de l'inventaire

#### Créer un article
```http
POST /api/v1/material/items
```

Enregistrez tous les articles de matériel liturgique :
- Aubes (avec tailles)
- Encensoirs
- Calices, patènes, ciboires
- Nappes d'autel
- Cierges
- Croix processionnelles
- Autre matériel

**Informations à renseigner** :
- Nom et catégorie
- Quantité disponible
- État (BON, A_NETTOYER, A_REPARER, HORS_SERVICE)
- Emplacement de stockage
- Date d'achat
- Photo (optionnel)

#### Suivre l'état du matériel
- Consultez l'inventaire complet
- Filtrez par catégorie ou état
- Recherchez un article spécifique
- Identifiez les articles nécessitant attention

---

### 2. Planification des tâches de nettoyage

#### Créer une tâche
```http
POST /api/v1/material/cleaning-tasks
```

Planifiez les tâches de nettoyage :
- Nettoyage des encensoirs
- Nettoyage des calices
- Entretien des nappes
- Maintenance des cierges

**Informations requises** :
- Titre et description
- Type de tâche
- Date et heure prévues
- Lieu
- Liste des articles concernés

#### Assigner des servants
```http
POST /api/v1/material/cleaning-tasks/{task_id}/assign
```

Assignez un ou plusieurs servants à chaque tâche. Les servants reçoivent une notification.

#### Suivi des tâches
- Consultez les tâches planifiées
- Suivez l'avancement (PLANIFIEE, EN_COURS, TERMINEE, VALIDEE)
- Validez le travail effectué

---

### 3. Gestion des aubes

#### Créer une tâche d'aubes
```http
POST /api/v1/material/aube-tasks
```

Planifiez le lavage et le repassage des aubes :
- Spécifiez le nombre d'aubes
- Indiquez les tailles concernées
- Définissez le lieu (buanderie, pressing)
- Activez la notification broadcast

**Notification broadcast** : Tous les utilisateurs sont informés de la disponibilité des aubes propres.

#### Workflow
1. Créer la tâche de lavage
2. Marquer comme terminée avec photos
3. Valider le travail
4. Créer la tâche de repassage
5. Valider et notifier

---

### 4. Historique de maintenance

#### Enregistrer une maintenance
```http
POST /api/v1/material/items/{item_id}/maintenance
```

Conservez l'historique complet :
- Type de maintenance
- Description détaillée
- Date d'exécution
- Coût (optionnel)
- Notes

**Mise à jour automatique** : La date de dernière maintenance de l'article est mise à jour automatiquement.

#### Planifier les maintenances
- Définissez la date de prochaine maintenance
- Recevez des alertes pour les maintenances à venir
- Consultez l'historique complet par article

---

### 5. Rapports et statistiques

#### Générer un rapport
```http
POST /api/v1/material/report
```

Générez des rapports détaillés :
- Inventaire complet
- Répartition par catégorie
- Répartition par état
- Tâches effectuées
- Coûts de maintenance
- Articles nécessitant attention

**Watermark** : Tous les rapports incluent le logo `logo_servant.jpeg`.

#### Statistiques en temps réel
```http
GET /api/v1/material/stats
```

Consultez les statistiques globales :
- Nombre total d'articles
- Taux de complétion des tâches
- Articles nécessitant maintenance
- Tâches en attente

---

## Workflows recommandés

### Workflow 1 : Nettoyage hebdomadaire

1. **Lundi** : Planifier les tâches de la semaine
2. **Mardi-Vendredi** : Assigner les servants
3. **Samedi** : Valider les tâches terminées
4. **Dimanche** : Vérifier que tout est prêt

### Workflow 2 : Lavage des aubes

1. **Collecte** : Rassembler les aubes sales
2. **Planification** : Créer la tâche de lavage
3. **Lavage** : Marquer comme terminée avec photos
4. **Validation** : Vérifier la qualité
5. **Repassage** : Créer la tâche de repassage
6. **Notification** : Broadcast à tous les servants

### Workflow 3 : Maintenance préventive

1. **Mensuel** : Consulter les articles nécessitant maintenance
2. **Planification** : Créer les tâches de maintenance
3. **Exécution** : Effectuer la maintenance
4. **Enregistrement** : Ajouter à l'historique avec coût
5. **Mise à jour** : Planifier la prochaine maintenance

---

## Bonnes pratiques

### Inventaire
- ✅ Photographiez chaque article
- ✅ Mettez à jour l'état régulièrement
- ✅ Indiquez l'emplacement précis
- ✅ Notez la date d'achat

### Tâches
- ✅ Planifiez à l'avance
- ✅ Assignez des servants disponibles
- ✅ Demandez des photos avant/après
- ✅ Validez rapidement le travail

### Aubes
- ✅ Lavez régulièrement (toutes les 2 semaines)
- ✅ Repassez immédiatement après lavage
- ✅ Vérifiez les tailles disponibles
- ✅ Notifiez tous les servants

### Maintenance
- ✅ Enregistrez tous les coûts
- ✅ Planifiez les maintenances préventives
- ✅ Conservez l'historique complet
- ✅ Anticipez les réparations

---

## Permissions

### INTENDANT / INTENDANT_ADJOINT
- ✅ Créer, modifier, supprimer des articles
- ✅ Créer, modifier, supprimer des tâches
- ✅ Assigner des servants
- ✅ Valider les tâches
- ✅ Ajouter des maintenances
- ✅ Générer des rapports

### Tous les utilisateurs authentifiés
- ✅ Consulter l'inventaire
- ✅ Consulter les tâches
- ✅ Marquer les tâches comme terminées
- ✅ Consulter l'historique
- ✅ Consulter les statistiques

---

## Notifications

### Assignation de tâche
Lorsqu'un servant est assigné à une tâche, il reçoit une notification avec :
- Titre de la tâche
- Date et heure
- Lieu
- Articles concernés

### Tâche d'aubes (broadcast)
Lorsqu'une tâche d'aubes est créée avec `broadcast_notification=true`, tous les utilisateurs reçoivent une notification.

---

## Traçabilité

Toutes les actions sont tracées :
- Qui a créé l'article
- Qui a créé la tâche
- Qui a assigné les servants
- Qui a validé le travail
- Qui a effectué la maintenance

---

## Exemples d'utilisation

### Exemple 1 : Ajouter un nouvel encensoir
```json
POST /api/v1/material/items
{
  "name": "Encensoir doré",
  "category": "ENCENSOIR",
  "description": "Encensoir en laiton doré",
  "quantity": 1,
  "condition": "BON",
  "location": "Sacristie - Armoire B",
  "purchase_date": "2025-01-15T00:00:00",
  "photo_url": "https://storage.example.com/encensoir.jpg"
}
```

### Exemple 2 : Planifier le nettoyage
```json
POST /api/v1/material/cleaning-tasks
{
  "title": "Nettoyage des encensoirs",
  "description": "Nettoyage complet après la messe",
  "task_type": "NETTOYAGE",
  "scheduled_date": "2026-03-01T10:00:00",
  "scheduled_time": "10h00",
  "location": "Sacristie",
  "items": ["Encensoir doré", "Encensoir argenté"]
}
```

### Exemple 3 : Lavage des aubes
```json
POST /api/v1/material/aube-tasks
{
  "title": "Lavage des aubes",
  "task_type": "LAVAGE",
  "scheduled_date": "2026-03-05T14:00:00",
  "scheduled_time": "14h00",
  "location": "Buanderie paroissiale",
  "aube_count": 15,
  "aube_sizes": ["S", "M", "L", "XL"],
  "broadcast_notification": true
}
```

### Exemple 4 : Enregistrer une maintenance
```json
POST /api/v1/material/items/{item_id}/maintenance
{
  "maintenance_type": "REPARATION",
  "description": "Réparation de la chaîne de l'encensoir",
  "performed_date": "2026-02-15T10:00:00",
  "cost": 2000.0,
  "notes": "Chaîne remplacée"
}
```

---

## Support

Pour toute question ou problème, contactez l'administrateur système ou consultez la documentation API complète dans `docs/22-API-MATERIAL.md`.

---

## Changelog

### Version 1.0.0 (2026-02-11)
- ✅ Gestion complète de l'inventaire
- ✅ Planification des tâches de nettoyage
- ✅ Gestion des aubes avec broadcast
- ✅ Historique de maintenance avec coûts
- ✅ Rapports avec watermark
- ✅ Statistiques en temps réel
- ✅ 25 endpoints API
- ✅ Tests E2E complets
