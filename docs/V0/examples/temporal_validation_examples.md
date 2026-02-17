# Exemples de Validation Temporelle

Ce document illustre comment la validation temporelle fonctionne pour différentes messes, qu'elles soient ordinaires ou exceptionnelles.

## Principe de Base

**Pour chaque messe**, la fenêtre de modification est calculée automatiquement :
- **Début** : `heure_messe - 1 heure`
- **Fin** : `heure_messe + 2 heures` (1h de messe + 1h après)

Le système utilise **l'heure spécifique** de chaque messe, qu'elle soit ordinaire ou exceptionnelle.

---

## Exemples pour Messes Ordinaires

### Dimanche 16 février 2026 - Horaires Ordinaires

| Messe | Heure | Langue | Fenêtre de Modification | Durée |
|-------|-------|--------|------------------------|-------|
| 1 | **06h30** | Ewondo | 05h30 → 08h30 | 3h |
| 2 | **08h30** | Français | 07h30 → 10h30 | 3h |
| 3 | **10h00** | Ewondo | 09h00 → 12h00 | 3h |
| 4 | **11h30** | Anglais | 10h30 → 13h30 | 3h |
| 5 | **17h00** | Français | 16h00 → 19h00 | 3h |

### Scénario 1 : Messe de 08h30

**Contexte** : Dimanche 16/02/2026, messe en français à 08h30

**Fenêtre autorisée** : 07h30 → 10h30

#### Tentatives de Modification

| Heure Actuelle | Action | Résultat | Explication |
|----------------|--------|----------|-------------|
| 07h00 | Ajouter servant | ❌ REFUSÉ | Trop tôt (avant 07h30) |
| 07h30 | Ajouter servant | ✅ AUTORISÉ | Dans la fenêtre |
| 08h00 | Marquer présence | ✅ AUTORISÉ | Dans la fenêtre |
| 08h30 | Ajouter remplaçant | ✅ AUTORISÉ | Pendant la messe |
| 09h15 | Marquer présence | ✅ AUTORISÉ | Après la messe |
| 10h30 | Marquer absence | ✅ AUTORISÉ | Dernière minute |
| 10h31 | Modifier | ❌ REFUSÉ | Trop tard (après 10h30) |
| 11h00 | Marquer présence | ❌ REFUSÉ | Fenêtre fermée |

**Message d'erreur** (si hors fenêtre) :
```json
{
  "detail": "Le marquage de présence n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

### Scénario 2 : Messe de 06h30

**Contexte** : Dimanche 16/02/2026, messe en ewondo à 06h30

**Fenêtre autorisée** : 05h30 → 08h30

#### Tentatives de Modification

| Heure Actuelle | Action | Résultat |
|----------------|--------|----------|
| 05h00 | Ajouter servant | ❌ REFUSÉ |
| 05h30 | Ajouter servant | ✅ AUTORISÉ |
| 06h30 | Marquer présence | ✅ AUTORISÉ |
| 07h30 | Marquer présence | ✅ AUTORISÉ |
| 08h30 | Marquer absence | ✅ AUTORISÉ |
| 08h31 | Modifier | ❌ REFUSÉ |

### Scénario 3 : Messe de 17h00

**Contexte** : Dimanche 16/02/2026, messe en français à 17h00

**Fenêtre autorisée** : 16h00 → 19h00

#### Tentatives de Modification

| Heure Actuelle | Action | Résultat |
|----------------|--------|----------|
| 15h30 | Ajouter servant | ❌ REFUSÉ |
| 16h00 | Ajouter servant | ✅ AUTORISÉ |
| 17h00 | Marquer présence | ✅ AUTORISÉ |
| 18h00 | Marquer présence | ✅ AUTORISÉ |
| 19h00 | Marquer absence | ✅ AUTORISÉ |
| 19h01 | Modifier | ❌ REFUSÉ |

---

## Exemples pour Messes Exceptionnelles

### Dimanche 23 février 2026 - Horaires Exceptionnels

**Contexte** : Dimanche avec horaires modifiés (fête spéciale, événement diocésain, etc.)

| Messe | Heure | Langue | Fenêtre de Modification | Durée |
|-------|-------|--------|------------------------|-------|
| 1 | **06h30** | Ewondo | 05h30 → 08h30 | 3h |
| 2 | **09h00** | Français/Ewondo | 08h00 → 11h00 | 3h |
| 3 | **11h30** | Anglais | 10h30 → 13h30 | 3h |
| 4 | **17h00** | Français | 16h00 → 19h00 | 3h |

### Scénario 4 : Messe Exceptionnelle de 09h00

**Contexte** : Dimanche 23/02/2026, messe bilingue français/ewondo à 09h00

**Fenêtre autorisée** : 08h00 → 11h00

#### Tentatives de Modification

| Heure Actuelle | Action | Résultat | Explication |
|----------------|--------|----------|-------------|
| 07h30 | Ajouter servant | ❌ REFUSÉ | Trop tôt (avant 08h00) |
| 08h00 | Ajouter servant | ✅ AUTORISÉ | Début de fenêtre |
| 08h30 | Marquer présence | ✅ AUTORISÉ | Dans la fenêtre |
| 09h00 | Ajouter remplaçant | ✅ AUTORISÉ | Pendant la messe |
| 10h00 | Marquer présence | ✅ AUTORISÉ | Après la messe |
| 11h00 | Marquer absence | ✅ AUTORISÉ | Fin de fenêtre |
| 11h01 | Modifier | ❌ REFUSÉ | Fenêtre fermée |

**Message d'erreur** (si hors fenêtre) :
```json
{
  "detail": "L'ajout de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 09h00."
}
```

### Scénario 5 : Messe Solennelle Exceptionnelle

**Contexte** : Dimanche 02/03/2026, messe solennelle à 10h30

**Fenêtre autorisée** : 09h30 → 12h30

#### Tentatives de Modification

| Heure Actuelle | Action | Résultat |
|----------------|--------|----------|
| 09h00 | Ajouter CEROFERERAIRE | ❌ REFUSÉ |
| 09h30 | Ajouter CEROFERERAIRE | ✅ AUTORISÉ |
| 10h00 | Ajouter CEREMONIAIRE | ✅ AUTORISÉ |
| 10h30 | Marquer présence | ✅ AUTORISÉ |
| 11h30 | Marquer présence | ✅ AUTORISÉ |
| 12h30 | Marquer absence | ✅ AUTORISÉ |
| 12h31 | Modifier | ❌ REFUSÉ |

---

## Cas d'Usage Réels

### Cas 1 : Servant Absent de Dernière Minute

**Situation** :
- Messe : Dimanche 08h30
- Heure actuelle : 08h15
- Problème : Le THURIFERAIRE prévu est absent

**Actions possibles** (toutes dans la fenêtre 07h30-10h30) :
1. ✅ Marquer l'absence du THURIFERAIRE prévu
2. ✅ Ajouter un remplaçant au poste THURIFERAIRE
3. ✅ Ajouter un CEROFERERAIRE supplémentaire si besoin

### Cas 2 : Vérification Post-Messe

**Situation** :
- Messe : Dimanche 08h30
- Heure actuelle : 09h45
- Tâche : Vérifier les présences effectives

**Actions possibles** (toutes dans la fenêtre 07h30-10h30) :
1. ✅ Marquer les présences confirmées
2. ✅ Marquer les absences constatées
3. ✅ Ajouter des servants qui ont servi mais n'étaient pas prévus

### Cas 3 : Tentative Tardive

**Situation** :
- Messe : Dimanche 08h30
- Heure actuelle : 11h00
- Tentative : Marquer une présence oubliée

**Résultat** : ❌ **REFUSÉ**

```json
{
  "detail": "Le marquage de présence n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de 08h30."
}
```

**Solution** : Contacter l'administrateur ou l'aumônier pour une correction manuelle.

### Cas 4 : Plusieurs Messes le Même Jour

**Situation** : Dimanche avec 5 messes

**Fenêtres indépendantes** :
- Messe 06h30 : fenêtre 05h30-08h30
- Messe 08h30 : fenêtre 07h30-10h30
- Messe 10h00 : fenêtre 09h00-12h00
- Messe 11h30 : fenêtre 10h30-13h30
- Messe 17h00 : fenêtre 16h00-19h00

**À 09h00** :
- ✅ Peut modifier la messe de 08h30 (fenêtre 07h30-10h30)
- ✅ Peut modifier la messe de 10h00 (fenêtre 09h00-12h00)
- ❌ Ne peut PAS modifier la messe de 06h30 (fenêtre fermée à 08h30)
- ❌ Ne peut PAS modifier la messe de 11h30 (fenêtre pas encore ouverte)
- ❌ Ne peut PAS modifier la messe de 17h00 (fenêtre pas encore ouverte)

---

## Implémentation Technique

### Code de Validation

```python
def is_within_mass_window(
    schedule_date: datetime,
    mass_time: str,
    current_time: Optional[datetime] = None
) -> bool:
    """
    Vérifie si l'heure actuelle est dans la fenêtre autorisée.
    
    Args:
        schedule_date: Date du dimanche (ex: 2026-02-16)
        mass_time: Heure de la messe (ex: "08h30", "09h00")
        current_time: Heure actuelle (None = maintenant)
    
    Returns:
        bool: True si dans la fenêtre autorisée
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Parser l'heure de la messe (ex: "08h30" → 8, 30)
    hours, minutes = parse_mass_time(mass_time)
    
    # Créer le datetime de début de la messe
    # Ex: 2026-02-16 08:30:00
    mass_start = schedule_date.replace(
        hour=hours,
        minute=minutes,
        second=0,
        microsecond=0
    )
    
    # Calculer la fenêtre
    # Ex: 07:30:00 → 10:30:00
    window_start = mass_start - timedelta(hours=1)
    window_end = mass_start + timedelta(hours=2)
    
    # Vérifier si l'heure actuelle est dans la fenêtre
    return window_start <= current_time <= window_end
```

### Utilisation dans le Service

```python
# Récupérer la messe et le template
mass = await self.schedule_repo.get_mass(mass_id)
template = await self.schedule_repo.get_template(mass.template_id)

# Validation temporelle avec l'heure SPÉCIFIQUE de cette messe
if not is_within_mass_window(template.schedule_date, mass.mass_time):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Action non autorisée en dehors de la fenêtre pour la messe de {mass.mass_time}."
    )
```

### Points Clés

1. **Chaque messe a sa propre fenêtre** : Le système utilise `mass.mass_time` qui contient l'heure spécifique de chaque messe
2. **Fonctionne pour ordinaires ET exceptionnelles** : Aucune différence dans le traitement
3. **Calcul automatique** : La fenêtre est calculée dynamiquement pour chaque messe
4. **Messages d'erreur précis** : Indiquent l'heure exacte de la messe concernée

---

## Résumé

✅ **Le système fonctionne déjà comme souhaité** :
- Chaque messe (ordinaire ou exceptionnelle) a sa propre fenêtre de modification
- La fenêtre est calculée à partir de l'heure spécifique de chaque messe
- Pour une messe à 08h30 : fenêtre de 07h30 à 10h30
- Pour une messe à 09h00 : fenêtre de 08h00 à 11h00
- Pour une messe à 17h00 : fenêtre de 16h00 à 19h00

✅ **Aucune différence entre ordinaire et exceptionnel** :
- Le système utilise simplement l'heure de la messe (`mass.mass_time`)
- Que cette heure soit 08h30 (ordinaire) ou 09h00 (exceptionnelle), le calcul est identique

✅ **Validation stricte** :
- Impossible de modifier avant le début de la fenêtre
- Impossible de modifier après la fin de la fenêtre
- Messages d'erreur clairs indiquant l'heure de la messe concernée
