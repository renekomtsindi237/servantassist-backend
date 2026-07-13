# Guide Utilisateur - Module CHARGE_SPORT_CULTURE

## Vue d'ensemble

Le module CHARGE_SPORT_CULTURE permet la gestion complète des activités sportives et culturelles du groupe de servants.

**Responsables** : CHARGE_SPORT_CULTURE et CHARGE_SPORT_CULTURE_ADJOINT

---

## Fonctionnalités principales

### 1. Planification des événements

#### Créer un événement
```http
POST /api/v1/sport-culture/events
```

Planifiez tous types d'activités :
- **Journées sportives** : Premier samedi du mois
- **Tournois** : Compétitions inter-paroisses
- **Matchs amicaux** : Rencontres sportives
- **Sorties culturelles** : Musées, monuments
- **Spectacles** : Théâtre, concerts
- **Visites** : Découvertes culturelles

**Informations à renseigner** :
- Titre et description
- Type d'événement et sport (si sportif)
- Date, heure de début et fin
- Lieu
- Nombre maximum de participants
- Coût par participant (optionnel)
- Date limite d'inscription
- Notification broadcast

#### Types d'événements sportifs
- Football, Basketball, Volleyball
- Handball, Athlétisme, Natation
- Tennis, et autres sports

---

### 2. Gestion des inscriptions

#### Inscrire des participants
```http
POST /api/v1/sport-culture/events/{event_id}/register
```

Inscrivez les servants aux événements :
- Inscription individuelle
- Inscription par lot
- Gestion des places disponibles
- Date limite d'inscription

#### Suivi des inscriptions
- Consultez la liste des inscrits
- Vérifiez les places restantes
- Confirmez les présences
- Gérez les annulations

---

### 3. Gestion des présences

#### Marquer la présence
```http
POST /api/v1/sport-culture/participations/{participation_id}/attendance
```

Suivez la présence des participants :
- INSCRIT : Inscription confirmée
- CONFIRME : Présence confirmée
- PRESENT : Présent à l'événement
- ABSENT : Absent
- EXCUSE : Absence excusée

#### Workflow de présence
1. Les servants s'inscrivent
2. Confirmez leur présence avant l'événement
3. Marquez la présence le jour J
4. Enregistrez les absences et excuses

---

### 4. Gestion des paiements

#### Marquer le paiement
```http
POST /api/v1/sport-culture/participations/{participation_id}/payment
```

Suivez les paiements :
- Coût par participant
- Statut de paiement
- Date de paiement
- Notes

**Calculs automatiques** :
- Coût total = coût × nombre de participants
- Revenu total = coût × nombre de paiements

---

### 5. Résultats sportifs

#### Enregistrer un résultat
```http
POST /api/v1/sport-culture/events/{event_id}/results
```

Conservez les résultats :
- Victoires, défaites, matchs nuls
- Scores des équipes
- Classements (pour les tournois)
- Descriptions détaillées

**Types de résultats** :
- VICTOIRE : Match gagné
- DEFAITE : Match perdu
- NUL : Match nul
- CLASSEMENT : Position au tournoi
- PARTICIPATION : Pour les activités culturelles

---

### 6. Gestion des équipes

#### Créer une équipe
```http
POST /api/v1/sport-culture/events/{event_id}/teams
```

Organisez les équipes :
- Nom de l'équipe
- Capitaine
- Liste des membres
- Enrichissement automatique avec noms

**Utilisation** :
- Tournois sportifs
- Matchs par équipes
- Compétitions

---

### 7. Rapports et statistiques

#### Générer un rapport
```http
POST /api/v1/sport-culture/report
```

Générez des rapports détaillés :
- Nombre total d'événements
- Répartition par type
- Nombre de participants
- Taux de participation moyen
- Coûts et revenus
- Top participants
- Résumé des événements

**Watermark** : Tous les rapports incluent le logo `logo_servant.jpeg`.

#### Statistiques en temps réel
```http
GET /api/v1/sport-culture/stats
```

Consultez les statistiques globales :
- Événements à venir
- Événements terminés
- Taux de participation
- Répartition par type et statut

#### Statistiques par servant
```http
GET /api/v1/sport-culture/servants/{servant_id}/stats
```

Suivez la participation de chaque servant :
- Nombre total de participations
- Événements assistés
- Événements manqués
- Taux de présence
- Total payé
- Répartition par type d'événement

---

## Workflows recommandés

### Workflow 1 : Journée sportive mensuelle

1. **J-15** : Créer l'événement avec broadcast
2. **J-10** : Ouvrir les inscriptions
3. **J-3** : Fermer les inscriptions
4. **J-1** : Confirmer les présences
5. **Jour J** : Marquer les présences
6. **J+1** : Enregistrer les résultats
7. **J+2** : Générer le rapport

### Workflow 2 : Tournoi inter-paroisses

1. **Planification** : Créer l'événement tournoi
2. **Inscriptions** : Inscrire les participants
3. **Équipes** : Créer les équipes
4. **Paiements** : Collecter les frais
5. **Jour J** : Marquer les présences
6. **Résultats** : Enregistrer les scores et classements
7. **Rapport** : Générer le rapport final

### Workflow 3 : Sortie culturelle

1. **Planification** : Créer l'événement visite
2. **Inscriptions** : Limiter le nombre de places
3. **Paiements** : Collecter les frais d'entrée
4. **Confirmation** : Confirmer les présences
5. **Jour J** : Marquer les présences
6. **Retour** : Enregistrer la participation
7. **Rapport** : Générer le rapport

---

## Bonnes pratiques

### Planification
- ✅ Planifiez les journées sportives le 1er samedi du mois
- ✅ Annoncez les événements 2 semaines à l'avance
- ✅ Utilisez la notification broadcast
- ✅ Fixez une date limite d'inscription

### Inscriptions
- ✅ Limitez le nombre de participants si nécessaire
- ✅ Fermez les inscriptions 3 jours avant
- ✅ Confirmez les présences la veille
- ✅ Gérez une liste d'attente si complet

### Présences
- ✅ Marquez les présences le jour même
- ✅ Enregistrez les excuses
- ✅ Suivez le taux de participation
- ✅ Contactez les absents récurrents

### Paiements
- ✅ Fixez un coût raisonnable
- ✅ Collectez avant l'événement
- ✅ Enregistrez immédiatement
- ✅ Suivez les impayés

### Résultats
- ✅ Enregistrez les résultats le jour même
- ✅ Soyez précis dans les descriptions
- ✅ Conservez les photos
- ✅ Partagez les résultats avec tous

---

## Permissions

### CHARGE_SPORT_CULTURE / CHARGE_SPORT_CULTURE_ADJOINT
- ✅ Créer, modifier, supprimer des événements
- ✅ Inscrire des participants
- ✅ Marquer les présences
- ✅ Gérer les paiements
- ✅ Enregistrer les résultats
- ✅ Créer des équipes
- ✅ Générer des rapports

### Tous les utilisateurs authentifiés
- ✅ Consulter les événements
- ✅ Consulter les participations
- ✅ Consulter les résultats
- ✅ Consulter les statistiques

---

## Notifications

### Création d'événement
Lorsqu'un événement est créé avec `broadcast_notification=true`, tous les utilisateurs reçoivent une notification avec :
- Titre de l'événement
- Date et heure
- Lieu
- Coût
- Date limite d'inscription

### Rappels
- Rappel 3 jours avant l'événement
- Rappel la veille pour confirmation
- Notification des résultats

---

## Traçabilité

Toutes les actions sont tracées :
- Qui a créé l'événement
- Qui a inscrit les participants
- Qui a marqué les présences
- Qui a enregistré les résultats
- Qui a créé les équipes

---

## Exemples d'utilisation

### Exemple 1 : Créer une journée sportive
```json
POST /api/v1/sport-culture/events
{
  "title": "Journée sportive d'avril",
  "description": "Football et basketball au stade",
  "event_type": "JOURNEE_SPORTIVE",
  "sport_type": "FOOTBALL",
  "date": "2026-04-05T09:00:00",
  "start_time": "09h00",
  "end_time": "17h00",
  "location": "Stade municipal",
  "max_participants": 30,
  "cost": 1000.0,
  "registration_deadline": "2026-04-02T23:59:59",
  "broadcast_notification": true
}
```

### Exemple 2 : Inscrire plusieurs servants
```json
POST /api/v1/sport-culture/events/{event_id}/register-batch
{
  "servant_ids": [
    "uuid1",
    "uuid2",
    "uuid3"
  ]
}
```

### Exemple 3 : Enregistrer un résultat
```json
POST /api/v1/sport-culture/events/{event_id}/results
{
  "result_type": "VICTOIRE",
  "team_name": "Les Servants",
  "score": 5,
  "opponent_name": "Paroisse Saint-Jean",
  "opponent_score": 2,
  "description": "Belle victoire de notre équipe"
}
```

### Exemple 4 : Créer une équipe
```json
POST /api/v1/sport-culture/events/{event_id}/teams
{
  "team_name": "Équipe Alpha",
  "captain_id": "uuid",
  "members": ["uuid1", "uuid2", "uuid3", "uuid4"]
}
```

### Exemple 5 : Sortie culturelle
```json
POST /api/v1/sport-culture/events
{
  "title": "Visite du musée national",
  "description": "Découverte de l'histoire du Cameroun",
  "event_type": "VISITE",
  "date": "2026-04-15T14:00:00",
  "start_time": "14h00",
  "end_time": "18h00",
  "location": "Musée National de Yaoundé",
  "max_participants": 20,
  "cost": 500.0,
  "registration_deadline": "2026-04-12T23:59:59",
  "broadcast_notification": true
}
```

---

## Calendrier type

### Mensuel
- **1er samedi** : Journée sportive
- **3ème samedi** : Sortie culturelle ou match

### Trimestriel
- **Fin de trimestre** : Tournoi inter-paroisses

### Annuel
- **Vacances** : Grand tournoi annuel
- **Fête patronale** : Spectacle culturel

---

## Support

Pour toute question ou problème, contactez l'administrateur système ou consultez la documentation API complète dans `docs/24-API-SPORT-CULTURE.md`.

---

## Changelog

### Version 1.0.0 (2026-02-11)
- ✅ Gestion complète des événements sportifs et culturels
- ✅ Inscriptions avec limite de participants
- ✅ Suivi des présences et paiements
- ✅ Enregistrement des résultats sportifs
- ✅ Gestion des équipes
- ✅ Rapports avec watermark
- ✅ Statistiques en temps réel
- ✅ Notifications broadcast
- ✅ 25+ endpoints API
- ✅ Tests E2E complets
