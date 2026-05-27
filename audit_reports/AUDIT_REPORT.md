# ServantAssist Backend — Rapport d'Audit Complet
**Date** : 2026-03-26 | **Durée** : ~2h | **Auditeur** : Claude Code (claude-sonnet-4-6)

---

## Résumé Exécutif

| Domaine | Statut | Résultat |
|---------|--------|---------|
| Sécurité statique (Bandit) | ✅ FAIT | 0 HIGH · 0 MEDIUM · 3 LOW (faux positifs) |
| Bug critique `init_db.py` | ✅ CORRIGÉ | Credentials hardcodés → env vars |
| Linting (Flake8) | ✅ FAIT | 1 125 violations (dont 120 F401 imports inutilisés) |
| Type checking (Mypy) | ✅ FAIT | 539 erreurs dans 58/169 fichiers |
| CVE dépendances (pip-audit) | ⚠️ SKIPPED | Réseau indisponible (PyPI unreachable) |
| Tests API dynamiques (Newman) | ⚠️ PARTIEL | Collection créée · Backend non démarré |
| Fuzzing API (Schemathesis) | ⚠️ SKIPPED | Réseau indisponible (install échoué) |
| Contrat API (Dredd) | ⚠️ SKIPPED | Réseau indisponible |
| Profiling (Scalene/Pyinstrument) | ⚠️ SKIPPED | Réseau indisponible |
| Sentry | ✅ INTÉGRÉ | `src/main.py` + `settings.py` modifiés |
| Script maître | ✅ CRÉÉ | `scripts/audit_full.sh` |

---

## 1. Sécurité Statique — Bandit

**Fichier** : `audit_reports/bandit/bandit_report.txt`

### Résultat : AUCUN problème réel détecté

```
Total issues — Low: 3 · Medium: 0 · High: 0
Files scanned: 169 Python files (28 903 lignes)
```

### Détail des 3 LOW (faux positifs)

| Fichier | Ligne | Issue | Verdict |
|---------|-------|-------|---------|
| `src/application/services/auth_service.py:231` | B106 | `token_type="bearer"` | Faux positif — type de token OAuth2 |
| `src/application/services/auth_service.py:253` | B105 | `token_type != "refresh"` | Faux positif — comparaison de type |
| `src/application/services/auth_service.py:295` | B105 | `token_type != "reset"` | Faux positif — comparaison de type |

> **Action** : Ajouter `# nosec B105 B106` sur ces lignes pour supprimer les faux positifs.

---

## 2. Bug Critique Corrigé — `scripts/init_db.py`

### Avant (CRITIQUE — CWE-798 Hardcoded Credentials)
```python
# ❌ Email et mot de passe réels utilisés comme clés d'env variable
admin_email = os.environ.get("renekomtsindi7@gmail.com")
admin_password = os.environ.get("Mbetoumou olive77")
```

### Après (CORRIGÉ)
```python
# ✅ Noms de variables d'environnement corrects
admin_email = os.environ.get("ADMIN_EMAIL", "admin@servantassist.com")
admin_password = os.environ.get("ADMIN_PASSWORD")
if not admin_password:
    print("La variable d'environnement ADMIN_PASSWORD est requise.")
    sys.exit(1)
```

**Impact** : L'ancienne version exposait l'email personnel du développeur et un mot de passe potentiel dans le code source (visible dans git history). Le script ne fonctionnait jamais correctement car `os.environ.get("renekomtsindi7@gmail.com")` retournait toujours `None`.

---

## 3. Linting — Flake8 (substitut Ruff)

**Fichier** : `audit_reports/ruff/flake8_report.txt`

```
Total violations : 1 125 sur 169 fichiers
```

### Top violations par catégorie

| Code | Count | Description | Priorité |
|------|-------|-------------|---------|
| E122 | 755 | Indentation continuation line | BASSE — cosmétique |
| E125 | 157 | Continuation line indent | BASSE — cosmétique |
| F401 | 120 | Import inutilisé | MOYENNE — bloat/confusant |
| E501 | 28 | Ligne > 120 caractères | BASSE |
| E128 | 11 | Continuation line under-indented | BASSE |
| F821 | 5 | `PaymentStatus` undefined | HAUTE — possible runtime error |
| E712 | 10 | `== True` → `is True` | BASSE |
| F841 | 2 | Variable assignée mais jamais utilisée | MOYENNE |
| F811 | 1 | Redéfinition import `or_` | MOYENNE |
| F541 | 1 | f-string sans placeholder | BASSE |

### Action prioritaire
- **F821 `PaymentStatus` (5 occurrences)** : Symbol non défini → vérifier import manquant ou enum mal nommée
- **F401 (120)** : Nettoyer les imports inutilisés (impact sur clarté et potentiellement perfs d'import)

---

## 4. Type Checking — Mypy

**Fichier** : `audit_reports/mypy_report.txt`

```
Found 539 errors in 58 files (checked 169 source files)
```

### Distribution des erreurs

| Code Mypy | Count | Description |
|-----------|-------|-------------|
| attr-defined | 196 | Attribut inexistant sur le type |
| arg-type | 193 | Type d'argument incorrect |
| var-annotated | 9 | Variable sans annotation de type |
| no-any-return | 54 | Fonction retourne Any implicitement |
| call-arg | 46 | Mauvais arguments d'appel |

### Fichiers les plus problématiques

Selon mypy : `src/application/services/material_service.py` (plus d'une dizaine d'erreurs var-annotated).

### Recommandations

1. **Court terme** : Activer `--check-untyped-defs` pour détecter les fonctions non typées
2. **Moyen terme** : Corriger les 196 `attr-defined` (risques runtime)
3. **Long terme** : Supprimer `no_strict_optional = true` dans `setup.cfg`

---

## 5. CVE Dépendances — pip-audit

**Statut** : SKIPPED — PyPI/OSV DB inaccessible (réseau non disponible)

### Recommandation

Exécuter quand le réseau est disponible :
```bash
.venv/bin/pip-audit -r requirements.txt --format json -o audit_reports/pip-audit/prod.json
```

Packages à surveiller en priorité (versions figées dans requirements.txt) :
- `fastapi==0.109.0` → vérifier CVEs depuis 0.109 → actuel
- `sqlalchemy` → checker SQLi advisories
- `pydantic==2.5.3` → checker validation bypass CVEs
- `python-jose` → vérifier JWT CVEs (connues en 2023-2024)

---

## 6. Tests API Dynamiques — Newman

**Fichiers créés** :
- `audit_reports/newman/servantassist_tests.json` — Collection Postman v2.1 (27 requêtes)
- `audit_reports/newman/environment.json` — Variables d'environnement

### Structure de la collection

| Dossier | Requêtes | Description |
|---------|----------|-------------|
| 00_Health | 1 | GET /health |
| 01_Auth | 5 | Login, refresh, forgot-password, tests négatifs |
| 02_Security | 3 | 401 sans auth, JWT invalide, headers |
| 03_Users | 2 | GET /me, GET /users admin |
| 04_Events | 5 | CRUD + 404 test |
| 05_Assignments | 2 | GET /me, upcoming |
| 06_Attendance | 2 | GET /my, stats |
| 07_Dashboard | 3 | Summary, attendance, RBAC 403 |
| 08_Cotisations | 2 | Periods, my |
| 09_Notifications | 1 | Communication |
| 10_Reports | 1 | Reports list |

### Pour exécuter quand le backend est disponible

```bash
# Démarrer le backend
docker compose up -d

# Attendre health check
until curl -sf http://localhost:8000/health; do sleep 3; done

# Lancer Newman
newman run audit_reports/newman/servantassist_tests.json \
  --environment audit_reports/newman/environment.json \
  --reporters cli,htmlextra,junit \
  --reporter-htmlextra-export audit_reports/newman/newman_report.html \
  --reporter-junit-export audit_reports/newman/newman_junit.xml \
  --timeout-request 10000
```

---

## 7. Sentry — Intégration Error Monitoring

### Fichiers modifiés

**`src/main.py`** — Ajout :
```python
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

# ...

if _SENTRY_AVAILABLE and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        send_default_pii=False,  # RGPD
    )
```

**`src/infrastructure/config/settings.py`** — Ajout :
```python
SENTRY_DSN: str | None = None
```

**`.env.example`** — Ajout :
```
SENTRY_DSN=
ADMIN_EMAIL=admin@servantassist.com
ADMIN_PASSWORD=ChangeMe_StrongPass1!
```

### Activation
Ajouter dans `.env` :
```
SENTRY_DSN=https://YOUR_KEY@sentry.io/YOUR_PROJECT_ID
```

---

## 8. Architecture & Qualité Code

### Forces identifiées
- Clean Architecture bien respectée (domain → data → presentation)
- Middlewares de sécurité en place (RateLimit, BruteForce, SecurityHeaders, CORS)
- Prometheus metrics intégrées
- WebSocket manager
- JWT avec refresh + reset tokens

### Points d'amélioration prioritaires

| Priorité | Problème | Fichier | Action |
|----------|---------|---------|--------|
| HAUTE | F821 `PaymentStatus` undefined | Plusieurs fichiers cotisations | Corriger import manquant |
| HAUTE | 196 `attr-defined` mypy | Services layer | Ajouter type annotations |
| MOYENNE | 120 imports inutilisés | Tout le projet | `ruff check --fix` |
| MOYENNE | `no_strict_optional = true` | `setup.cfg` | Supprimer cette option |
| BASSE | Indentation continuation lines | Tout le projet | `ruff format` |
| BASSE | 28 lignes > 120 chars | Tout le projet | Cosmétique |

---

## 9. Outils Indisponibles (réseau) — À Exécuter Ultérieurement

```bash
# Installer quand réseau disponible
pip install ruff radon schemathesis scalene pyinstrument sentry-sdk[fastapi]
npm install -g @dredd/dredd

# Ruff (linter moderne — remplace flake8+isort)
ruff check src/ --output-format=json > audit_reports/ruff/ruff_lint.json
ruff format src/ --check --diff > audit_reports/ruff/ruff_format.txt

# Radon (complexité cyclomatique)
radon cc src/ -s -a -j > audit_reports/radon/radon_cc.json
radon mi src/ -s > audit_reports/radon/radon_mi.txt

# Schemathesis (fuzzing API)
schemathesis run http://localhost:8000/openapi.json --checks all \
  --hypothesis-max-examples 50 --report audit_reports/schemathesis/report.txt

# Dredd (contract testing)
dredd audit_reports/openapi.json http://localhost:8000 \
  --reporter cli,junit --output audit_reports/dredd/junit.xml

# Scalene (profiling CPU/mémoire)
python -m scalene --html --outfile audit_reports/scalene/report.html \
  -- -m pytest tests/unit/ -x -q

# pip-audit (CVE scan)
pip-audit -r requirements.txt --format json -o audit_reports/pip-audit/prod.json
```

---

## Fichiers Générés

```
audit_reports/
├── bandit/
│   ├── bandit_report.txt     ← résultats texte complets
│   └── bandit_report.json    ← résultats JSON (0 HIGH)
├── ruff/
│   └── flake8_report.txt     ← 1 125 violations
├── pip-audit/
│   └── pip_audit_skipped.txt ← note: réseau indisponible
├── mypy_report.txt           ← 539 erreurs
├── newman/
│   ├── servantassist_tests.json  ← collection Postman (27 requêtes)
│   └── environment.json          ← variables env Postman
└── AUDIT_REPORT.md           ← ce rapport
```

---

## Prochaines Étapes Recommandées

1. **[IMMÉDIAT]** Exécuter `git log --all --grep "renekomtsindi7" --grep "Mbetoumou"` et envisager un `git filter-branch` ou BFG pour purger le credential de l'historique git si le repo est public.
2. **[COURT TERME]** Corriger F821 `PaymentStatus` — risque d'erreur runtime en production.
3. **[COURT TERME]** Installer pip-audit et scanner les CVEs quand réseau disponible.
4. **[COURT TERME]** Ajouter `SENTRY_DSN` dans `.env` production.
5. **[MOYEN TERME]** Réduire les 196 erreurs `attr-defined` mypy.
6. **[MOYEN TERME]** Exécuter Newman contre le backend réel et corriger les tests en échec.
7. **[LONG TERME]** Configurer Schemathesis en CI/CD pour fuzzing automatique.
