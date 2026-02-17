# Module CHARGE_LITURGIE - Guide Utilisateur

Guide complet pour l'utilisation du module de formations liturgiques.

---

## Vue d'Ensemble

Le module CHARGE_LITURGIE permet de gérer toutes les formations liturgiques du groupe de servants avec un système complet de planification, suivi et évaluation.

---

## Fonctionnalités Principales

### 1. Planification des Sessions

Créez des sessions de formation adaptées à tous les niveaux :

**Niveaux disponibles :**
- **DEBUTANT** : Nouveaux servants
- **INTERMEDIAIRE** : Servants confirmés
- **AVANCE** : Servants expérimentés
- **TOUS** : Tous niveaux

**Informations requises :**
- Titre et description
- Objectifs pédagogiques
- Date, heure et durée
- Lieu de formation
- Formateur
- Nombre maximum de participants (0 = illimité)

**Exemple :**
```json
{
  "title": "Formation liturgique de base",
  "description": "Introduction aux gestes liturgiques fondamentaux",
  "objectives": "Maîtriser les gestes de base : génuflexion, inclination, port de la croix",
  "level": "DEBUTANT",
  "date": "2026-02-15T14:00:00",
  "start_time": "14h00",
  "end_time": "16h00",
  "duration_minutes": 120,
  "location": "Salle paroissiale",
  "max_participants": 20
}
```

### 2. Gestion des Inscriptions

Inscrivez les servants aux sessions :

**Inscription individuelle :**
- Sélectionner le servant
- Ajouter des notes si nécessaire

**Inscription par lot :**
- Sélectionner plusieurs servants
- Inscription en une seule opération

**Limites :**
- Vérification du nombre maximum de participants
- Pas de double inscription
- Pas d'inscription aux sessions terminées/annulées

### 3. Suivi de Présence

Marquez la présence pendant la session :

**Statuts disponibles :**
- **INSCRIT** : Inscrit mais pas encore présent
- **PRESENT** : Présent à la session
- **ABSENT** : Absent non excusé
- **EXCUSE** : Absent excusé

**Workflow :**
1. Ouvrir la liste des participants
2. Marquer chaque participant
3. Ajouter des notes si nécessaire

### 4. Évaluation des Participants

Évaluez les participants après la formation :

**Critères d'évaluation :**
- Note sur 100
- Commentaires détaillés
- Délivrance de certificat

**Exemple :**
```json
{
  "evaluation_score": 85,
  "evaluation_comments": "Très bonne participation. Maîtrise correcte des gestes de base. À approfondir : port de l'encensoir.",
  "certificate_issued": true
}
```

### 5. Bibliothèque de Ressources

Gérez les matériels pédagogiques :

**Types de matériels :**
- **DOCUMENT** : PDF, Word, PowerPoint
- **VIDEO** : Vidéos de démonstration
- **QUIZ** : Quiz d'évaluation
- **IMAGE** : Photos, schémas
- **AUTRE** : Autres types

**Caractéristiques :**
- Titre et description
- Niveau concerné
- Tags pour la recherche
- Visibilité (public/privé)
- Compteur de vues

**Exemple :**
```json
{
  "title": "Guide du servant d'autel",
  "description": "Document PDF complet avec tous les gestes liturgiques illustrés",
  "type": "DOCUMENT",
  "level": "DEBUTANT",
  "tags": ["liturgie", "gestes", "formation", "guide"],
  "is_public": true
}
```

### 6. Statistiques et Rapports

Suivez la progression des servants :

**Statistiques par servant :**
- Nombre total de sessions
- Taux de présence
- Note moyenne
- Nombre de certificats obtenus
- Date de la dernière formation

**Rapports de formation :**
- Période personnalisable
- Filtrage par niveau
- Taux de présence moyen
- Note moyenne
- Répartition par niveau
- Meilleurs participants

---

## Cas d'Usage

### Cas 1 : Formation de Nouveaux Servants

**Situation :** Accueil de 5 nouveaux servants

**Actions :**
1. Créer une session "Formation de base" (niveau DEBUTANT)
2. Préparer les matériels pédagogiques
3. Inscrire les 5 nouveaux servants
4. Animer la formation
5. Marquer la présence
6. Évaluer chaque participant
7. Délivrer les certificats

### Cas 2 : Formation Continue

**Situation :** Formation mensuelle pour tous les servants

**Actions :**
1. Créer une session "Formation continue" (niveau TOUS)
2. Inscrire tous les servants intéressés
3. Animer la formation
4. Marquer la présence
5. Évaluer les participants
6. Générer le rapport mensuel

### Cas 3 : Formation Spécialisée

**Situation :** Formation avancée sur l'encensement

**Actions :**
1. Créer une session "Maîtrise de l'encensoir" (niveau AVANCE)
2. Limiter à 10 participants
3. Inscrire les servants expérimentés
4. Préparer une vidéo de démonstration
5. Animer la formation pratique
6. Évaluer avec note élevée requise
7. Délivrer les certificats

---

## Bonnes Pratiques

### 1. Planification

✅ **À FAIRE :**
- Planifier à l'avance (au moins 1 semaine)
- Définir des objectifs clairs
- Préparer les matériels
- Limiter le nombre si nécessaire

❌ **À ÉVITER :**
- Planification de dernière minute
- Objectifs vagues
- Manque de matériels
- Surcharge de participants

### 2. Animation

✅ **À FAIRE :**
- Commencer à l'heure
- Suivre les objectifs
- Utiliser les matériels
- Encourager la participation

❌ **À ÉVITER :**
- Retards répétés
- Improvisation totale
- Manque de supports
- Cours magistral uniquement

### 3. Évaluation

✅ **À FAIRE :**
- Évaluer tous les participants
- Commentaires constructifs
- Critères objectifs
- Délivrer les certificats mérités

❌ **À ÉVITER :**
- Oublier d'évaluer
- Commentaires vagues
- Notation arbitraire
- Certificats systématiques

### 4. Suivi

✅ **À FAIRE :**
- Consulter les statistiques
- Identifier les besoins
- Adapter les formations
- Générer des rapports réguliers

❌ **À ÉVITER :**
- Ignorer les statistiques
- Formations répétitives
- Manque de progression
- Pas de rapports

---

## Permissions

### CHARGE_LITURGIE / CHARGE_LITURGIE_ADJOINT

✅ Créer des sessions de formation
✅ Modifier des sessions
✅ Supprimer des sessions
✅ Inscrire des participants
✅ Marquer la présence
✅ Évaluer les participants
✅ Créer des matériels pédagogiques
✅ Modifier des matériels
✅ Supprimer des matériels
✅ Générer des rapports

### Tous les utilisateurs authentifiés

✅ Consulter les sessions
✅ Consulter les matériels publics
✅ Consulter leurs propres participations
✅ Consulter leurs propres statistiques

---

## Traçabilité

Toutes les actions sont tracées :

- **Qui** : ID du CHARGE_LITURGIE
- **Quand** : Date et heure
- **Quoi** : Action effectuée
- **Où** : Session/Matériel concerné

---

## Dépannage

### Problème : Impossible d'inscrire un servant

**Cause 1 :** Session pleine
**Solution :** Augmenter le nombre maximum de participants ou créer une nouvelle session

**Cause 2 :** Servant déjà inscrit
**Solution :** Vérifier la liste des participants

**Cause 3 :** Session terminée/annulée
**Solution :** Créer une nouvelle session

### Problème : Certificat non généré

**Cause :** Fonctionnalité en développement
**Solution :** Utiliser un modèle de certificat externe temporairement

---

## Support

- **Documentation API** : `/docs/20-API-TRAINING.md`
- **Email** : support@servantassist.com

---

## Changelog

### Version 1.0.0 (2026-02-11)

- ✅ Planification de sessions de formation
- ✅ Gestion des inscriptions (individuelle et par lot)
- ✅ Marquage de présence
- ✅ Évaluation des participants
- ✅ Bibliothèque de ressources pédagogiques
- ✅ Statistiques par servant
- ✅ Rapports de formation
- ✅ Traçabilité complète
- ✅ Logo en filigrane sur les rapports
- ⏳ Génération automatique de certificats (à venir)
