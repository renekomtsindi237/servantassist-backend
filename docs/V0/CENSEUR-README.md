# Module CENSEUR - Guide Utilisateur

Guide complet pour l'utilisation du module de gestion des appels.

---

## Vue d'Ensemble

Le module CENSEUR permet de gérer les appels hebdomadaires des servants, effectués chaque samedi après la messe de 06h15. Il offre un suivi complet de la présence et génère des statistiques pour la discipline.

---

## Fonctionnalités Principales

### 1. Gestion des Sessions d'Appel

Créez et gérez les sessions d'appel hebdomadaires.

#### Créer une Session

```
POST /api/v1/attendance-sessions/
```

**Quand ?** Chaque samedi après la messe de 06h15

**Informations requises :**
- Date de la session (samedi)
- Heure de l'appel (défaut: 07h30)
- Lieu (défaut: Sacristie)
- Notes optionnelles

**Exemple :**
```json
{
  "session_date": "2026-02-08T00:00:00",
  "session_time": "07h30",
  "location": "Sacristie",
  "notes": "Appel du samedi 8 février"
}
```

### 2. Marquage de Présence

Enregistrez la présence de chaque servant.

#### Statuts Disponibles

- **PRESENT** : Servant présent à l'heure
- **ABSENT** : Servant absent sans justification
- **LATE** : Servant en retard
- **EXCUSED** : Absence justifiée

#### Marquer un Servant

```
POST /api/v1/attendance-sessions/{session_id}/records
```

**Exemple - Présent :**
```json
{
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "status": "PRESENT",
  "arrival_time": "07h25"
}
```

**Exemple - Retard :**
```json
{
  "servant_id": "222e4567-e89b-12d3-a456-426614174000",
  "status": "LATE",
  "arrival_time": "08h00",
  "notes": "Arrivé en retard"
}
```

**Exemple - Absent :**
```json
{
  "servant_id": "333e4567-e89b-12d3-a456-426614174000",
  "status": "ABSENT",
  "notes": "Absence non justifiée"
}
```

### 3. Modification d'Enregistrements

Modifiez un enregistrement si un justificatif est fourni.

```
PATCH /api/v1/attendance-sessions/records/{record_id}
```

**Exemple - Passer de ABSENT à EXCUSED :**
```json
{
  "status": "EXCUSED",
  "notes": "Justificatif médical fourni"
}
```

### 4. Liste des Servants

Obtenez la liste complète des servants pour l'appel.

```
GET /api/v1/attendance-sessions/servants/list
```

**Réponse :**
```json
[
  {
    "id": "111e4567-e89b-12d3-a456-426614174000",
    "first_name": "Jean",
    "last_name": "Dupont",
    "email": "jean.dupont@test.com",
    "phone_number": "+237600000001"
  }
]
```

### 5. Statistiques de Présence

Consultez les statistiques d'un servant.

```
GET /api/v1/attendance-sessions/servants/{servant_id}/stats
```

**Réponse :**
```json
{
  "servant_name": "Jean Dupont",
  "total_sessions": 52,
  "present_count": 45,
  "absent_count": 3,
  "late_count": 2,
  "excused_count": 2,
  "attendance_rate": 86.54,
  "consecutive_absences": 0
}
```

**Indicateurs :**
- **Taux de présence** : Pourcentage de présences
- **Absences consécutives** : Alerte si > 2
- **Retards** : Nombre de retards

### 6. Rapports de Présence

Générez des rapports pour une période donnée.

```
POST /api/v1/attendance-sessions/report
```

**Exemple - Rapport Mensuel :**
```json
{
  "start_date": "2026-02-01T00:00:00",
  "end_date": "2026-02-28T23:59:59",
  "include_stats": true
}
```

**Contenu du Rapport :**
- Nombre total de sessions
- Taux de présence global
- Statistiques par session
- Statistiques par servant
- Logo en filigrane (logo_servant.jpeg)

---

## Workflow Hebdomadaire

### Samedi Matin - Avant l'Appel

1. **Créer la session d'appel**
   ```bash
   POST /api/v1/attendance-sessions/
   {
     "session_date": "2026-02-08T00:00:00",
     "notes": "Appel du samedi"
   }
   ```

2. **Récupérer la liste des servants**
   ```bash
   GET /api/v1/attendance-sessions/servants/list
   ```

### Pendant l'Appel

3. **Marquer chaque servant**
   - Présents : Statut PRESENT
   - Retards : Statut LATE + heure d'arrivée
   - Absents : Statut ABSENT

### Après l'Appel

4. **Vérifier les enregistrements**
   ```bash
   GET /api/v1/attendance-sessions/{session_id}
   ```

5. **Modifier si nécessaire**
   - Si un justificatif arrive plus tard
   - Passer de ABSENT à EXCUSED

---

## Cas d'Usage

### Cas 1 : Appel Normal

**Situation :** Samedi matin, 25 servants attendus

**Actions :**
1. Créer la session
2. Marquer les 23 présents
3. Marquer 1 retard (arrivé à 08h00)
4. Marquer 1 absent

**Résultat :** Taux de présence = 92%

### Cas 2 : Justificatif Tardif

**Situation :** Un servant absent fournit un justificatif médical lundi

**Actions :**
1. Trouver l'enregistrement du servant
2. Modifier le statut : ABSENT → EXCUSED
3. Ajouter note : "Justificatif médical fourni"

### Cas 3 : Rapport Mensuel

**Situation :** Fin du mois, besoin de statistiques

**Actions :**
1. Générer rapport du 1er au 28 février
2. Analyser le taux de présence global
3. Identifier les servants avec absences répétées
4. Exporter le rapport avec logo

### Cas 4 : Alerte Discipline

**Situation :** Un servant a 3 absences consécutives

**Actions :**
1. Consulter ses statistiques
2. Vérifier `consecutive_absences`
3. Si ≥ 3 : Signaler au responsable
4. Prendre mesures disciplinaires

---

## Bonnes Pratiques

### 1. Création de Sessions

✅ **À FAIRE :**
- Créer la session le samedi matin
- Utiliser des notes descriptives
- Vérifier que la date est un samedi

❌ **À ÉVITER :**
- Créer plusieurs sessions pour le même samedi
- Oublier de créer la session
- Créer des sessions pour des dates passées

### 2. Marquage de Présence

✅ **À FAIRE :**
- Marquer tous les servants
- Noter l'heure pour les retards
- Ajouter des notes pour les absences

❌ **À ÉVITER :**
- Oublier de marquer certains servants
- Marquer deux fois le même servant
- Ne pas noter les retards

### 3. Modification d'Enregistrements

✅ **À FAIRE :**
- Modifier uniquement avec justificatif
- Ajouter une note explicative
- Modifier rapidement après réception du justificatif

❌ **À ÉVITER :**
- Modifier sans raison valable
- Modifier des sessions trop anciennes
- Oublier d'ajouter une note

### 4. Génération de Rapports

✅ **À FAIRE :**
- Générer des rapports mensuels
- Inclure les statistiques détaillées
- Archiver les rapports

❌ **À ÉVITER :**
- Générer des rapports trop fréquemment
- Oublier de générer les rapports mensuels
- Ne pas analyser les statistiques

---

## Interprétation des Statistiques

### Taux de Présence

- **≥ 90%** : Excellent
- **80-89%** : Bon
- **70-79%** : Moyen (à surveiller)
- **< 70%** : Faible (action requise)

### Absences Consécutives

- **0-1** : Normal
- **2** : À surveiller
- **≥ 3** : Alerte discipline

### Retards

- **0-2 par mois** : Acceptable
- **3-5 par mois** : À surveiller
- **> 5 par mois** : Problème récurrent

---

## Permissions

### CENSEUR

✅ Créer des sessions
✅ Marquer la présence
✅ Modifier les enregistrements
✅ Consulter les statistiques
✅ Générer des rapports

### CENSEUR_ADJOINT

✅ Créer des sessions
✅ Marquer la présence
✅ Modifier les enregistrements
✅ Consulter les statistiques
✅ Générer des rapports

### Autres Utilisateurs

👁️ Consulter les sessions
👁️ Consulter leurs propres statistiques
❌ Créer ou modifier

---

## Traçabilité

Toutes les actions sont tracées :

- **Qui** : ID du CENSEUR qui a effectué l'action
- **Quand** : Date et heure de l'action
- **Quoi** : Type d'action (création, modification)
- **Où** : Session et enregistrement concernés

**Exemple de traçabilité :**
```json
{
  "action": "mark_attendance",
  "performed_by": "789e4567-e89b-12d3-a456-426614174000",
  "performed_at": "2026-02-08T07:30:00",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "servant_id": "111e4567-e89b-12d3-a456-426614174000",
  "status": "PRESENT"
}
```

---

## Intégration avec Autres Modules

### Module DISCIPLINE

Les statistiques d'appel alimentent le module DISCIPLINE :
- Absences répétées → Dossier disciplinaire
- Retards fréquents → Avertissement
- Taux de présence faible → Sanction

### Module CLASSEMENT

Les censeurs ont accès à l'historique des classements :
- Vérifier les assignations passées
- Analyser la participation aux messes
- Identifier les servants actifs

---

## Dépannage

### Problème : Impossible de créer une session

**Causes possibles :**
- Vous n'êtes pas CENSEUR/CENSEUR_ADJOINT
- La date n'est pas un samedi
- Une session existe déjà pour cette date

**Solution :**
1. Vérifier vos permissions
2. Vérifier que la date est un samedi
3. Consulter les sessions existantes

### Problème : Impossible de marquer un servant

**Causes possibles :**
- Le servant est déjà marqué
- L'ID du servant est invalide
- La session n'existe pas

**Solution :**
1. Vérifier si le servant est déjà marqué
2. Vérifier l'ID du servant
3. Vérifier que la session existe

### Problème : Statistiques incorrectes

**Causes possibles :**
- Période de calcul incorrecte
- Enregistrements manquants
- Données corrompues

**Solution :**
1. Vérifier la période de calcul
2. Vérifier que tous les servants sont marqués
3. Contacter l'administrateur

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

# Créer une session
session_data = {
    "session_date": "2026-02-08T00:00:00",
    "notes": "Appel du samedi"
}
response = requests.post(
    f"{API_URL}/attendance-sessions/",
    headers=HEADERS,
    json=session_data
)
session = response.json()

# Marquer présence
record_data = {
    "servant_id": "111e4567-e89b-12d3-a456-426614174000",
    "status": "PRESENT",
    "arrival_time": "07h25"
}
response = requests.post(
    f"{API_URL}/attendance-sessions/{session['id']}/records",
    headers=HEADERS,
    json=record_data
)

# Générer rapport
report_data = {
    "start_date": "2026-02-01T00:00:00",
    "end_date": "2026-02-28T23:59:59",
    "include_stats": True
}
response = requests.post(
    f"{API_URL}/attendance-sessions/report",
    headers=HEADERS,
    json=report_data
)
report = response.json()
print(f"Taux de présence global: {report['overall_attendance_rate']}%")
```

### JavaScript

```javascript
const API_URL = "http://localhost:8000/api/v1";
const TOKEN = "votre_token_jwt";

// Créer une session
async function createSession() {
  const response = await fetch(`${API_URL}/attendance-sessions/`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      session_date: "2026-02-08T00:00:00",
      notes: "Appel du samedi"
    })
  });
  return await response.json();
}

// Marquer présence
async function markAttendance(sessionId, servantId) {
  const response = await fetch(
    `${API_URL}/attendance-sessions/${sessionId}/records`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${TOKEN}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        servant_id: servantId,
        status: "PRESENT",
        arrival_time: "07h25"
      })
    }
  );
  return await response.json();
}
```

---

## Support

Pour toute question ou problème :

- **Documentation API** : `/docs/17-API-ATTENDANCE-SESSIONS.md`
- **Email** : support@servantassist.com
- **Téléphone** : +237 XXX XXX XXX

---

## Changelog

### Version 1.0.0 (2026-02-10)

- ✅ Création de sessions d'appel
- ✅ Marquage de présence (4 statuts)
- ✅ Modification d'enregistrements
- ✅ Statistiques par servant
- ✅ Génération de rapports
- ✅ Liste complète des servants
- ✅ Traçabilité complète
- ✅ Logo en filigrane sur rapports

