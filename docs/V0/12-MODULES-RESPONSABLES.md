# Modules des Responsables

Ce document décrit les fonctionnalités spécifiques pour chaque responsable du groupe de servants.

---

## 1. Module ECONOME - Gestion Financière

### Fonctionnalités

#### 1.1 Contributions Mensuelles
- **Modes de paiement** :
  - Hebdomadaire : 100 FCFA/samedi (4 samedis = 400 FCFA/mois)
  - Mensuel : 500 FCFA/mois (paiement unique)
- **Suivi** : Cocher chaque paiement reçu
- **Traçabilité** : Qui a payé, quand, combien, mode de paiement

#### 1.2 Bilan Financier
- Rapport complet des contributions par période
- Filtrage par date (début → fin)
- Export avec logo_servant.jpeg en filigrane
- Statistiques : taux de paiement, montants collectés, servants en retard

#### 1.3 Permissions
- **ECONOME** : Créer, modifier, consulter toutes les contributions
- **COMMISSAIRE_AUX_COMPTES** : Consulter uniquement (audit)
- **Admin/Aumônier** : Accès complet

---

## 2. Module CENSEUR - Gestion de la Discipline

### Fonctionnalités

#### 2.1 Appel Hebdomadaire
- **Séance** : Chaque samedi après la messe de 06h15
- **Liste** : Tous les servants (rôle SERVANT)
- **Marquage** : Présent / Absent / Retard / Excusé
- **Traçabilité** : Date, heure, qui a fait l'appel

#### 2.2 Historique de Présence
- Taux de présence par servant
- Absences répétées (alertes)
- Export des statistiques
- Rapport disciplinaire

#### 2.3 Permissions
- **CENSEUR** : Créer et modifier les appels
- **CENSEUR_ADJOINT** : Créer et modifier les appels
- **Admin/Aumônier** : Accès complet
- **Autres responsables** : Consultation uniquement

---

## 3. Module SECRETAIRE - Gestion Administrative

### Fonctionnalités

#### 3.1 Rapports de Réunions
- **Réunions hebdomadaires** : Compte-rendu structuré
- **Contenu** : Date, participants, ordre du jour, décisions, actions
- **Visibilité** : Tous les responsables + aumônier
- **Export** : PDF avec logo_servant.jpeg en filigrane

#### 3.2 Rapports d'Activités
- Activités du groupe (sorties, événements, formations)
- Photos et documents joints
- Archivage structuré

#### 3.3 Permissions
- **SECRETAIRE** : Créer, modifier, publier
- **SECRETAIRE_ADJOINT** : Créer, modifier, publier
- **Responsables + Aumônier** : Consultation
- **Admin** : Accès complet

---

## 4. Module COMMISSAIRE_AUX_COMPTES - Audit Financier

### Fonctionnalités

#### 4.1 Traçabilité des Entrées
- **Sources** : Contributions, dons, événements
- **Enregistrement** : Date, montant, source, référence
- **Catégorisation** : Type de revenu
- **Validation** : Vérification des montants

#### 4.2 Bilan Financier
- Rapport d'audit complet
- Comparaison contributions attendues vs reçues
- Écarts et anomalies
- Export avec logo_servant.jpeg en filigrane

#### 4.3 Permissions
- **COMMISSAIRE_AUX_COMPTES** : Consultation + audit
- **ECONOME** : Collaboration (partage de données)
- **Admin/Aumônier** : Accès complet

---

## 5. Module CHARGE_LITURGIE - Formation Liturgique

### Fonctionnalités

#### 5.1 Planification des Formations
- **Modules** : Cours théoriques et pratiques
- **Calendrier** : Date, heure, lieu, formateur
- **Contenu** : Titre, description, objectifs, supports
- **Participants** : Tous les servants (inscription)

#### 5.2 Gestion des Sessions
- Création de sessions de formation
- Suivi de présence
- Évaluation des participants
- Certificats de formation

#### 5.3 Bibliothèque de Ressources
- Documents liturgiques
- Vidéos de démonstration
- Quiz et exercices
- Accessible à tous les utilisateurs authentifiés

#### 5.4 Permissions
- **CHARGE_LITURGIE** : Créer, modifier, animer
- **CHARGE_LITURGIE_ADJOINT** : Créer, modifier, animer
- **Responsables** : Consultation et participation
- **Servants** : Consultation et participation
- **Admin/Aumônier** : Accès complet

---

## 6. Module INTENDANTS - Gestion du Matériel

### Fonctionnalités

#### 6.1 Inventaire du Matériel
- **Aubes** : Nombre, tailles, état
- **Matériel liturgique** : Encensoirs, cierges, nappes, etc.
- **État** : Bon / À nettoyer / À réparer / Hors service
- **Traçabilité** : Historique des mouvements

#### 6.2 Planification du Nettoyage
- **Assignation** : Servants assignés au nettoyage
- **Calendrier** : Date et heure de nettoyage
- **Objets** : Liste des objets à nettoyer
- **Notification** : Tous les servants assignés sont notifiés

#### 6.3 Planification du Lavage/Repassage des Aubes
- **Assignation** : Servants pour lavage et repassage
- **Rotation** : Système équitable
- **Calendrier** : Date et heure
- **Notification** : Broadcast à tous les utilisateurs

#### 6.4 Suivi et Validation
- Marquage des tâches effectuées
- Photos avant/après
- Validation par les intendants

#### 6.5 Permissions
- **INTENDANT_MATERIEL** : Créer, modifier, assigner
- **INTENDANT_MATERIEL_ADJOINT** : Créer, modifier, assigner
- **Servants assignés** : Marquer tâche effectuée
- **Tous les utilisateurs** : Recevoir notifications
- **Admin/Aumônier** : Accès complet

---

## 7. Module CHARGE_SPORT_CULTURE - Activités Sportives et Culturelles

### Fonctionnalités

#### 7.1 Journées Sportives Mensuelles
- **Récurrence** : Premier samedi de chaque mois
- **Planification** : Activités, horaires, lieu
- **Inscription** : Servants participants
- **Notification** : Broadcast à tous les utilisateurs

#### 7.2 Rencontres Sportives
- **Événements** : Matchs, tournois, compétitions
- **Équipes** : Constitution et gestion
- **Résultats** : Scores et classements
- **Photos** : Galerie d'événements

#### 7.3 Activités Culturelles
- **Événements** : Sorties, spectacles, visites
- **Planification** : Date, lieu, programme
- **Participants** : Liste et inscription
- **Budget** : Coûts et contributions

#### 7.4 Notifications
- **Assignation** : Notification individuelle
- **Broadcast** : Notification à tous avec liste des participants
- **Rappels** : 24h avant l'événement

#### 7.5 Permissions
- **CHARGE_SPORT_CULTURE** : Créer, modifier, organiser
- **Participants** : S'inscrire, consulter
- **Tous les utilisateurs** : Recevoir notifications
- **Admin/Aumônier** : Accès complet

---

## Architecture Technique

### Entités Principales

```
1. Contribution (ECONOME)
   - servant_id, amount, payment_mode, payment_date, month, year
   - recorded_by, notes

2. Attendance (CENSEUR)
   - session_date, servant_id, status (PRESENT/ABSENT/LATE/EXCUSED)
   - recorded_by, notes

3. Report (SECRETAIRE)
   - type (MEETING/ACTIVITY), title, content, date
   - created_by, attachments, published

4. FinancialEntry (COMMISSAIRE_AUX_COMPTES)
   - date, amount, source, category, reference
   - verified_by, notes

5. TrainingSession (CHARGE_LITURGIE)
   - title, description, date, duration, location
   - trainer_id, materials, max_participants

6. TrainingParticipation
   - session_id, servant_id, attended, evaluation

7. MaterialItem (INTENDANTS)
   - name, category, quantity, condition, location
   - last_maintenance_date

8. CleaningTask (INTENDANTS)
   - date, time, items, assigned_servants
   - status, validated_by

9. AubeTask (INTENDANTS)
   - date, time, task_type (WASH/IRON), assigned_servants
   - status, validated_by

10. SportCultureEvent (CHARGE_SPORT_CULTURE)
    - title, type, date, location, description
    - participants, created_by
```

### Notifications

Toutes les assignations et événements déclenchent des notifications :
- Email
- WhatsApp (si configuré)
- Notification in-app

### Exports et Rapports

Tous les rapports incluent :
- Logo en filigrane (logo_servant.jpeg)
- Date de génération
- Signature du responsable
- Export PDF

---

## Priorisation de l'Implémentation

### Phase 1 (Priorité HAUTE)
1. ✅ Module ECONOME - Contributions
2. ✅ Module CENSEUR - Appels

### Phase 2 (Priorité MOYENNE)
3. ✅ Module SECRETAIRE - Rapports
4. ✅ Module COMMISSAIRE_AUX_COMPTES - Audit

### Phase 3 (Priorité MOYENNE)
5. ✅ Module CHARGE_LITURGIE - Formations
6. ✅ Module INTENDANTS - Matériel

### Phase 4 (Priorité BASSE)
7. ✅ Module CHARGE_SPORT_CULTURE - Activités

---

## Permissions Globales

| Rôle | Contributions | Appels | Rapports | Audit | Formations | Matériel | Sport/Culture |
|------|--------------|--------|----------|-------|------------|----------|---------------|
| ADMIN | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet |
| AUMÔNIER | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet | ✅ Complet |
| ECONOME | ✅ Gestion | 👁️ Lecture | 👁️ Lecture | 🤝 Collab | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture |
| CENSEUR | 👁️ Lecture | ✅ Gestion | 👁️ Lecture | ❌ | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture |
| SECRETAIRE | 👁️ Lecture | 👁️ Lecture | ✅ Gestion | ❌ | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture |
| COMMISSAIRE | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture | ✅ Audit | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture |
| CHARGE_LITURGIE | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture | ❌ | ✅ Gestion | 👁️ Lecture | 👁️ Lecture |
| INTENDANT | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture | ❌ | 👁️ Lecture | ✅ Gestion | 👁️ Lecture |
| CHARGE_SPORT | 👁️ Lecture | 👁️ Lecture | 👁️ Lecture | ❌ | 👁️ Lecture | 👁️ Lecture | ✅ Gestion |
| SERVANT | 👁️ Mes contrib | 👁️ Mes appels | 👁️ Lecture | ❌ | ✅ Participer | ✅ Tâches | ✅ Participer |

Légende :
- ✅ Gestion complète (CRUD)
- 👁️ Lecture seule
- 🤝 Collaboration
- ❌ Pas d'accès
