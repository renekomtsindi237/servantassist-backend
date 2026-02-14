# Validation Temporelle des Modifications

## Vue d'ensemble

Le système de classement implémente une **validation temporelle stricte** pour garantir que les modifications (ajout de servants, marquage de présence) ne peuvent être effectuées que pendant une fenêtre de temps appropriée autour de chaque messe.

## Règles de Validation

### Fenêtre de Modification Autorisée

**Pour chaque messe** :
- ⏰ **Début** : 1 heure avant le début de la messe
- ⏰ **Fin** : 1 heure après la fin de la messe (estimée à 1h)

**Durée totale de la fenêtre** : 3 heures
- 1h avant
- 1h pendant (durée estimée de la messe)
- 1h après

### Exemple Concret

Pour une messe de **08h30** :

```
07h30 ────────────────────────────────────────────────> 10h30
  │                                                        │
  │                                                        │
Début de la fenêtre                              Fin de la fenêtre
(1h avant)                                       (1h après la fin)

        08h30 ──────────> 09h30
        │                   │
    Début messe         Fin messe
                        (estimée)
```

**Modifications autorisées** : Entre 07h30 et 10h30
**Modifications refusées** : Avant 07h30 ou après 10h30

## Actions Concernées

### Classement Dominical (Sunday Schedule)

#### 1. Marquage de Présence/Absence

```bash
PATCH /api/v1/sunday-schedule/assignments/{assignment_id}/presence
{
  "is_present": true
}
```

**Validation** :
- ✅ Autorisé : 1h avant → 1h après la messe
- ❌ Refusé : En dehors de cette fenêtre

**Message d'erreur** :
```json
{
  "detail": "Le marquage de présence n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

#### 2. Ajout de Servants

```bash
POST /api/v1/sunday-schedule/masses/{mass_id}/assignments
{
  "position": "CEROFERERAIRE",
  "servant_name": "Jean DUPONT"
}
```

**Validation** :
- ✅ Autorisé : 1h avant → 1h après la messe
- ❌ Refusé : En dehors de cette fenêtre

**Message d'erreur** :
```json
{
  "detail": "L'ajout de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

#### 3. Retrait de Servants

```bash
DELETE /api/v1/sunday-schedule/assignments/{assignment_id}
```

**Validation** :
- ✅ Autorisé : 1h avant → 1h après la messe
- ❌ Refusé : En dehors de cette fenêtre

**Message d'erreur** :
```json
{
  "detail": "Le retrait de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

### Classement Hebdomadaire (Weekly Schedule)

#### 1. Ajout de Servants

```bash
POST /api/v1/weekly-schedule/slots/{slot_id}/servants
{
  "servant_name": "Jean DUPONT"
}
```

**Validation** :
- ✅ Autorisé : 1h avant → 1h après la messe
- ❌ Refusé : En dehors de cette fenêtre

**Message d'erreur** :
```json
{
  "detail": "L'ajout de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 06h15 le LUNDI."
}
```

**Note** : La date du créneau est calculée en trouvant le jour de la semaine correspondant (LUNDI, MARDI, etc.) dans la période définie par `start_date` et `end_date` du template.

#### 2. Retrait de Servants

```bash
DELETE /api/v1/weekly-schedule/assignments/{assignment_id}
```

**Validation** :
- ✅ Autorisé : 1h avant → 1h après la messe
- ❌ Refusé : En dehors de cette fenêtre

**Message d'erreur** :
```json
{
  "detail": "Le retrait de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 12h00 le MERCREDI."
}
```

## Cas d'Usage

### Scénario 1 : Dimanche Normal

**Messes du dimanche 16/02/2026** :

| Messe | Fenêtre de modification |
|-------|------------------------|
| 06h30 | 05h30 → 08h30 |
| 08h30 | 07h30 → 10h30 |
| 10h00 | 09h00 → 12h00 |
| 11h30 | 10h30 → 13h30 |
| 17h00 | 16h00 → 19h00 |

### Scénario 2 : Servant Absent de Dernière Minute

**Situation** : Il est 08h15, la messe de 08h30 commence dans 15 minutes.

**Actions possibles** :
1. ✅ Marquer l'absence du servant prévu
2. ✅ Ajouter un remplaçant (CEROFERERAIRE supplémentaire)
3. ✅ Modifier les assignations

**Jusqu'à** : 10h30 (1h après la fin estimée)

### Scénario 3 : Vérification Post-Messe

**Situation** : Il est 09h45, la messe de 08h30 vient de se terminer.

**Actions possibles** :
1. ✅ Marquer les présences effectives
2. ✅ Marquer les absences
3. ✅ Ajouter des servants qui ont servi mais n'étaient pas prévus

**Jusqu'à** : 10h30

### Scénario 4 : Tentative Tardive

**Situation** : Il est 11h00, on veut marquer la présence pour la messe de 08h30.

**Résultat** : ❌ **REFUSÉ**

```json
{
  "detail": "Le marquage de présence n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

## Implémentation Technique

### Fonction de Validation

Cette fonction est implémentée dans les deux services :
- `src/application/services/sunday_schedule_service.py`
- `src/application/services/weekly_schedule_service.py`

```python
def parse_mass_time(mass_time: str) -> tuple[int, int]:
    """
    Parse une heure de messe (ex: "06h30", "12h00") en heures et minutes.
    
    Returns:
        tuple[int, int]: (heures, minutes)
    """
    parts = mass_time.lower().replace('h', ':').split(':')
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours, minutes


def is_within_mass_window(
    schedule_date: datetime,
    mass_time: str,
    current_time: Optional[datetime] = None
) -> bool:
    """
    Vérifie si l'heure actuelle est dans la fenêtre autorisée.
    
    Args:
        schedule_date: Date du dimanche (ou du jour de semaine)
        mass_time: Heure de la messe (ex: "08h30", "06h15")
        current_time: Heure actuelle (None = maintenant)
    
    Returns:
        bool: True si dans la fenêtre autorisée
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Parser l'heure de la messe
    hours, minutes = parse_mass_time(mass_time)
    
    # Créer le datetime de début de la messe
    mass_start = schedule_date.replace(
        hour=hours,
        minute=minutes,
        second=0,
        microsecond=0
    )
    
    # Fenêtre : 1h avant → 2h après le début
    window_start = mass_start - timedelta(hours=1)
    window_end = mass_start + timedelta(hours=2)
    
    return window_start <= current_time <= window_end
```

### Utilisation dans les Services

#### Classement Dominical

```python
# Validation avant toute modification
if not is_within_mass_window(template.schedule_date, mass.mass_time):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Action non autorisée en dehors de la fenêtre de modification pour la messe de {mass.mass_time}."
    )
```

#### Classement Hebdomadaire

```python
# Calculer la date du créneau (jour de la semaine dans la période)
day_mapping = {
    DayOfWeek.LUNDI: 0,
    DayOfWeek.MARDI: 1,
    DayOfWeek.MERCREDI: 2,
    DayOfWeek.JEUDI: 3,
    DayOfWeek.VENDREDI: 4,
    DayOfWeek.SAMEDI: 5,
}

target_weekday = day_mapping[slot.day]
current_date = template.start_date
slot_date = None

while current_date <= template.end_date:
    if current_date.weekday() == target_weekday:
        slot_date = current_date
        break
    current_date += timedelta(days=1)

# Validation temporelle
if not is_within_mass_window(slot_date, slot.mass_time):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Action non autorisée en dehors de la fenêtre de modification pour la messe de {slot.mass_time} le {slot.day.value}."
    )
```

## Exceptions et Cas Particuliers

### 1. Création Initiale du Classement

**Quand** : Avant le dimanche (ex: le samedi)

**Validation** : ❌ **Pas de validation temporelle**

Le CHARGE_CLASSEMENT_DIMANCHE peut créer et remplir le classement à tout moment avant le dimanche.

### 2. Publication du Classement

**Quand** : Avant le dimanche

**Validation** : ❌ **Pas de validation temporelle**

La publication peut se faire à tout moment.

### 3. Modifications Pendant la Fenêtre

**Qui** : Tous les utilisateurs authentifiés

**Validation** : ✅ **Validation temporelle stricte**

Pendant la fenêtre de chaque messe, n'importe quel utilisateur authentifié peut :
- Marquer les présences
- Ajouter des servants (ex: remplaçants)
- Retirer des servants

### 4. Consultation de l'Historique

**Quand** : À tout moment

**Validation** : ❌ **Pas de validation temporelle**

L'historique est consultable à tout moment par les personnes autorisées.

## Avantages du Système

### 1. Flexibilité

- ✅ Permet les ajustements de dernière minute
- ✅ Permet les remplacements d'urgence
- ✅ Permet la vérification post-messe

### 2. Sécurité

- ✅ Empêche les modifications tardives
- ✅ Garantit l'intégrité des données historiques
- ✅ Traçabilité complète de toutes les actions

### 3. Réalisme

- ✅ Correspond au déroulement réel des messes
- ✅ Prend en compte les imprévus
- ✅ Permet la gestion en temps réel

## Diagramme de Flux

```
┌─────────────────────────────────────────────────────────────┐
│                    Tentative de Modification                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ Récupérer la messe  │
            │ et le template      │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ Calculer la fenêtre │
            │ de modification     │
            │ (1h avant → 1h après)│
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ Heure actuelle dans │
            │ la fenêtre ?        │
            └─────────┬───────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
        OUI                       NON
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│ ✅ Autoriser    │      │ ❌ Refuser      │
│ la modification │      │ HTTP 400        │
└─────────────────┘      └─────────────────┘
```

## Configuration

### Paramètres Modifiables

Si besoin d'ajuster les fenêtres, modifier dans `sunday_schedule_service.py` :

```python
# Fenêtre actuelle : 1h avant → 2h après le début
window_start = mass_start - timedelta(hours=1)  # Modifier ici
window_end = mass_start + timedelta(hours=2)    # Modifier ici
```

### Durée Estimée de la Messe

Actuellement : **1 heure**

Pour modifier :
```python
# Durée de la messe + temps après
window_end = mass_start + timedelta(hours=DUREE_MESSE + TEMPS_APRES)
```

## Tests

### Test 1 : Dans la Fenêtre

```python
# Messe à 08h30 le 16/02/2026
# Test à 08h00 (30 min avant)
assert is_within_mass_window(
    datetime(2026, 2, 16),
    "08h30",
    datetime(2026, 2, 16, 8, 0)
) == True
```

### Test 2 : Hors Fenêtre (Trop Tôt)

```python
# Test à 07h00 (1h30 avant)
assert is_within_mass_window(
    datetime(2026, 2, 16),
    "08h30",
    datetime(2026, 2, 16, 7, 0)
) == False
```

### Test 3 : Hors Fenêtre (Trop Tard)

```python
# Test à 11h00 (2h30 après le début)
assert is_within_mass_window(
    datetime(2026, 2, 16),
    "08h30",
    datetime(2026, 2, 16, 11, 0)
) == False
```
