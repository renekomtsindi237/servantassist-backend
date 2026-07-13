# Module SECRETAIRE - Guide Utilisateur

Guide complet pour l'utilisation du module de gestion des rapports.

---

## Vue d'Ensemble

Le module SECRETAIRE permet de gérer les rapports de réunions hebdomadaires et d'activités du groupe de servants. Il offre un système complet de rédaction, publication et archivage des rapports avec gestion des pièces jointes.

---

## Fonctionnalités Principales

### 1. Gestion des Rapports

Créez et gérez deux types de rapports :
- **Réunions (REUNION)** : Comptes-rendus des réunions hebdomadaires
- **Activités (ACTIVITE)** : Rapports des activités du groupe

#### Créer un Rapport

```
POST /api/v1/reports/
```

**Informations requises :**
- Type de rapport (REUNION ou ACTIVITE)
- Titre descriptif
- Contenu détaillé
- Date et heure
- Lieu
- Liste des participants (optionnel)
- Décisions prises (optionnel)
- Actions à mener (optionnel)

**Exemple - Rapport de Réunion :**
```json
{
  "type": "REUNION",
  "title": "Réunion hebdomadaire du 8 février 2026",
  "content": "Ordre du jour:\n1. Point sur les activités du mois\n2. Préparation de la retraite\n3. Questions diverses",
  "report_date": "2026-02-08T15:00:00",
  "location": "Salle paroissiale",
  "participants": [
    "Jean Dupont (Délégué)",
    "Pierre Martin (Secrétaire)",
    "Marie Dubois (Trésorière)"
  ],
  "decisions": "Décision de programmer une retraite spirituelle le 15 mars",
  "action_items": "- Réserver le lieu (Jean)\n- Préparer le programme (Pierre)\n- Gérer les inscriptions (Marie)"
}
```

**Exemple - Rapport d'Activité :**
```json
{
  "type": "ACTIVITE",
  "title": "Sortie au sanctuaire Notre-Dame",
  "content": "Sortie organisée le samedi 15 février avec 25 servants.\n\nProgramme:\n- 9h00: Départ de la paroisse\n- 10h30: Arrivée au sanctuaire\n- 11h00: Messe\n- 12h30: Déjeuner\n- 14h00: Visite guidée\n- 16h00: Retour",
  "report_date": "2026-02-15T09:00:00",
  "location": "Sanctuaire Notre-Dame",
  "participants": ["Tous les servants"]
}
```

### 2. Workflow de Publication

#### Étape 1 : Brouillon

Tous les rapports sont créés en statut **BROUILLON**.

- Visible uniquement par les secrétaires
- Modifiable à volonté
- Pièces jointes ajoutables
- Supprimable si nécessaire

#### Étape 2 : Modification

Modifiez le rapport autant que nécessaire avant publication.

```
PATCH /api/v1/reports/{report_id}
```

**Exemple :**
```json
{
  "title": "Réunion hebdomadaire du 8 février 2026 (modifié)",
  "content": "Contenu mis à jour...",
  "decisions": "Décisions mises à jour..."
}
```

#### Étape 3 : Publication

Publiez le rapport pour le rendre visible à tous les responsables.

```
POST /api/v1/reports/{report_id}/publish
```

**Après publication :**
- Visible par tous les responsables + aumônier
- Non modifiable
- Non supprimable
- Pièces jointes non modifiables

#### Étape 4 : Archivage (Optionnel)

Archivez les rapports anciens pour les retirer de la liste active.

```
POST /api/v1/reports/{report_id}/archive
```

### 3. Gestion des Pièces Jointes

Ajoutez des documents aux rapports (photos, PDF, etc.).

#### Ajouter une Pièce Jointe

```
POST /api/v1/reports/{report_id}/attachments
```

**Exemple :**
```json
{
  "filename": "compte_rendu_reunion.pdf",
  "file_url": "https://storage.example.com/files/compte_rendu_reunion.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000
}
```

**Types de fichiers supportés :**
- PDF : Comptes-rendus, documents officiels
- Images : Photos d'activités (JPEG, PNG)
- Documents : Word, Excel (si nécessaire)

**Limitations :**
- Pièces jointes uniquement sur brouillons
- Taille recommandée : < 10 MB par fichier
- Noms de fichiers descriptifs

#### Consulter les Pièces Jointes

```
GET /api/v1/reports/{report_id}/attachments
```

#### Supprimer une Pièce Jointe

```
DELETE /api/v1/reports/attachments/{attachment_id}
```

**Note :** Uniquement sur les rapports en brouillon.

### 4. Consultation des Rapports

#### Liste des Rapports

```
GET /api/v1/reports/
```

**Filtres disponibles :**
- Type : REUNION ou ACTIVITE
- Statut : BROUILLON, PUBLIE, ARCHIVE
- Période : start_date et end_date
- Pagination : skip et limit

**Exemple :**
```
GET /api/v1/reports/?report_type=REUNION&status=PUBLIE&start_date=2026-02-01T00:00:00&end_date=2026-02-28T23:59:59
```

#### Mes Rapports

Consultez uniquement vos rapports.

```
GET /api/v1/reports/me/list
```

#### Détail d'un Rapport

```
GET /api/v1/reports/{report_id}
```

---

## Cas d'Usage

### Cas 1 : Rapport de Réunion Hebdomadaire

**Situation :** Samedi après-midi, réunion des responsables

**Actions :**
1. Créer le rapport en brouillon
2. Rédiger l'ordre du jour et le contenu
3. Lister les participants
4. Noter les décisions prises
5. Lister les actions à mener
6. Ajouter le compte-rendu en PDF (si disponible)
7. Relire et corriger
8. Publier le rapport

**Résultat :** Tous les responsables peuvent consulter le rapport.

### Cas 2 : Rapport d'Activité

**Situation :** Sortie du groupe le samedi

**Actions :**
1. Créer le rapport d'activité
2. Décrire le déroulement de la journée
3. Ajouter des photos de l'activité
4. Mentionner les points positifs et à améliorer
5. Publier le rapport

**Résultat :** Traçabilité de l'activité pour les archives.

### Cas 3 : Modification Avant Publication

**Situation :** Erreur dans le rapport en brouillon

**Actions :**
1. Consulter le rapport
2. Identifier l'erreur
3. Modifier le rapport (PATCH)
4. Vérifier la correction
5. Publier

**Résultat :** Rapport correct publié.

### Cas 4 : Archivage de Rapports Anciens

**Situation :** Fin d'année, nettoyage des rapports

**Actions :**
1. Lister les rapports publiés de l'année précédente
2. Archiver les rapports anciens
3. Conserver les rapports importants publiés

**Résultat :** Liste active allégée, archives organisées.

---

## Bonnes Pratiques

### 1. Rédaction de Rapports

✅ **À FAIRE :**
- Rédiger rapidement après la réunion/activité
- Utiliser un titre descriptif et daté
- Structurer le contenu (ordre du jour, points abordés)
- Lister tous les participants
- Documenter toutes les décisions
- Assigner les actions avec responsables

❌ **À ÉVITER :**
- Attendre plusieurs jours pour rédiger
- Titres vagues ("Réunion")
- Contenu non structuré
- Oublier des participants
- Décisions non documentées
- Actions sans responsable

### 2. Gestion des Brouillons

✅ **À FAIRE :**
- Créer en brouillon d'abord
- Relire attentivement
- Vérifier l'orthographe
- Ajouter toutes les pièces jointes
- Publier rapidement

❌ **À ÉVITER :**
- Publier sans relecture
- Laisser des brouillons incomplets
- Oublier des pièces jointes
- Publier trop tard

### 3. Pièces Jointes

✅ **À FAIRE :**
- Noms de fichiers descriptifs
- Format PDF pour documents officiels
- Compresser les images volumineuses
- Vérifier que les fichiers s'ouvrent

❌ **À ÉVITER :**
- Noms génériques ("document.pdf")
- Fichiers trop volumineux (> 10 MB)
- Formats non standards
- Fichiers corrompus

### 4. Publication

✅ **À FAIRE :**
- Publier dans les 24h
- Vérifier que tout est complet
- Informer les responsables
- Archiver les rapports anciens

❌ **À ÉVITER :**
- Publier des brouillons incomplets
- Oublier de publier
- Publier trop tard
- Ne jamais archiver

---

## Permissions

### SECRETAIRE

✅ Créer des rapports
✅ Modifier des brouillons
✅ Supprimer des brouillons
✅ Publier des rapports
✅ Archiver des rapports
✅ Ajouter des pièces jointes
✅ Supprimer des pièces jointes
✅ Consulter tous les rapports

### SECRETAIRE_ADJOINT

✅ Créer des rapports
✅ Modifier des brouillons
✅ Supprimer des brouillons
✅ Publier des rapports
✅ Archiver des rapports
✅ Ajouter des pièces jointes
✅ Supprimer des pièces jointes
✅ Consulter tous les rapports

### Autres Responsables

👁️ Consulter les rapports publiés
👁️ Télécharger les pièces jointes
❌ Créer ou modifier

---

## Traçabilité

Toutes les actions sont tracées :

- **Qui** : ID du SECRETAIRE qui a effectué l'action
- **Quand** : Date et heure de l'action
- **Quoi** : Type d'action (création, modification, publication)

**Exemple de traçabilité :**
```json
{
  "action": "create_report",
  "performed_by": "789e4567-e89b-12d3-a456-426614174000",
  "performed_at": "2026-02-08T15:30:00",
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "report_type": "REUNION"
}
```

---

## Dépannage

### Problème : Impossible de créer un rapport

**Causes possibles :**
- Vous n'êtes pas SECRETAIRE/SECRETAIRE_ADJOINT
- Données invalides
- Connexion perdue

**Solution :**
1. Vérifier vos permissions
2. Vérifier les données (titre, contenu, date)
3. Vérifier la connexion internet

### Problème : Impossible de modifier un rapport

**Causes possibles :**
- Le rapport est déjà publié
- Vous n'êtes pas SECRETAIRE
- L'ID du rapport est invalide

**Solution :**
1. Vérifier le statut du rapport (doit être BROUILLON)
2. Vérifier vos permissions
3. Vérifier l'ID du rapport

### Problème : Impossible d'ajouter une pièce jointe

**Causes possibles :**
- Le rapport est déjà publié
- Le fichier est trop volumineux
- L'URL du fichier est invalide

**Solution :**
1. Vérifier le statut du rapport (doit être BROUILLON)
2. Compresser le fichier si nécessaire
3. Vérifier l'URL du fichier

### Problème : Les responsables ne voient pas mon rapport

**Causes possibles :**
- Le rapport est en brouillon
- Le rapport n'est pas publié

**Solution :**
1. Publier le rapport (POST /reports/{id}/publish)
2. Vérifier que le statut est PUBLIE

---

## Exemples de Code

### Python

```python
import requests

# Configuration
API_URL = "http://localhost:8000/api/v1"
TOKEN = "votre_token_jwt"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Créer un rapport
report_data = {
    "type": "REUNION",
    "title": "Réunion hebdomadaire",
    "content": "Ordre du jour...",
    "report_date": "2026-02-08T15:00:00",
    "location": "Salle paroissiale",
    "participants": ["Jean", "Pierre"]
}
response = requests.post(
    f"{API_URL}/reports/",
    headers=HEADERS,
    json=report_data
)
report = response.json()

# Ajouter une pièce jointe
attachment_data = {
    "filename": "compte_rendu.pdf",
    "file_url": "https://example.com/compte_rendu.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000
}
response = requests.post(
    f"{API_URL}/reports/{report['id']}/attachments",
    headers=HEADERS,
    json=attachment_data
)

# Publier le rapport
response = requests.post(
    f"{API_URL}/reports/{report['id']}/publish",
    headers=HEADERS
)
published_report = response.json()
print(f"Rapport publié: {published_report['title']}")
```

### JavaScript

```javascript
const API_URL = "http://localhost:8000/api/v1";
const TOKEN = "votre_token_jwt";

// Créer un rapport
async function createReport() {
  const response = await fetch(`${API_URL}/reports/`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      type: "REUNION",
      title: "Réunion hebdomadaire",
      content: "Ordre du jour...",
      report_date: "2026-02-08T15:00:00",
      location: "Salle paroissiale",
      participants: ["Jean", "Pierre"]
    })
  });
  return await response.json();
}

// Publier un rapport
async function publishReport(reportId) {
  const response = await fetch(
    `${API_URL}/reports/${reportId}/publish`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${TOKEN}`
      }
    }
  );
  return await response.json();
}
```

---

## Support

Pour toute question ou problème :

- **Documentation API** : `/docs/18-API-REPORTS.md`
- **Email** : support@servantassist.com
- **Téléphone** : +237 XXX XXX XXX

---

## Changelog

### Version 1.0.0 (2026-02-10)

- ✅ Création de rapports (réunions et activités)
- ✅ Modification de rapports en brouillon
- ✅ Publication de rapports
- ✅ Archivage de rapports
- ✅ Gestion des pièces jointes
- ✅ Filtrage et pagination
- ✅ Traçabilité complète
- ✅ Logo en filigrane sur rapports

