# ServantAssist Backend — Guide de dépannage

## Erreurs de démarrage

### `connection refused` — PostgreSQL
```
asyncpg.exceptions.ConnectionRefusedError: [Errno 111] Connect call failed
```
**Cause :** PostgreSQL non démarré ou mauvaise URL.
**Solution :**
```bash
docker compose up postgres -d       # Démarrer PostgreSQL
echo $DATABASE_URL                  # Vérifier la variable
psql $DATABASE_URL -c "SELECT 1;"  # Tester la connexion
```

### `connection refused` — Redis
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```
**Solution :**
```bash
docker compose up redis -d
redis-cli ping  # Doit répondre PONG
```

### `Module not found` — import error au démarrage
**Cause :** Environnement virtuel non activé.
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Erreurs d'authentification JWT

### `401 Unauthorized` — Token expiré
```json
{"detail": "Token expiré. Reconnectez-vous."}
```
**Solution :** L'app mobile/Angular doit rafraîchir avec `POST /auth/refresh-token`.

### `401 Unauthorized` — Token sur liste noire (Redis)
**Cause :** L'utilisateur s'est déconnecté mais utilise encore l'ancien token.
**Solution :** Se reconnecter et obtenir un nouveau token.

### `401 Unauthorized` — Mauvaise clé secrète
**Cause :** `SECRET_KEY` différente entre l'émetteur et le vérificateur (ex. redéploiement).
**Solution :** Vérifier que `SECRET_KEY` est identique dans `.env` et en production.

---

## Erreurs de migrations Alembic

### Migration qui échoue
```bash
alembic upgrade head  # → ERROR: column already exists
```
**Solution :**
```bash
# 1. Voir l'état actuel
alembic current
alembic history --verbose

# 2. Rollback d'une migration
alembic downgrade -1

# 3. Corriger le fichier de migration, puis réessayer
alembic upgrade head
```

### `Multiple head revisions`
```bash
alembic merge -m "merge heads" <rev1> <rev2>
alembic upgrade head
```

---

## Erreurs Celery

### Worker ne démarre pas
```bash
celery -A src.infrastructure.tasks.celery_app worker --loglevel=debug
# Vérifier :
# 1. Redis accessible
# 2. Imports corrects dans les tâches
# 3. REDIS_URL dans .env
```

### Beat ne lance pas les tâches
```bash
# Vérifier le timezone
grep timezone src/infrastructure/tasks/celery_app.py
# Doit être : Africa/Douala

# Lister les tâches planifiées
celery -A src.infrastructure.tasks.celery_app inspect scheduled
```

### Tâche bloquée en `PENDING`
```bash
# Voir les tâches actives
celery -A src.infrastructure.tasks.celery_app inspect active

# Révoquer une tâche
celery -A src.infrastructure.tasks.celery_app control revoke <task-id>
```

---

## Erreurs de chiffrement (Loi 2024/017)

### `Invalid key` — Erreur AES-256-GCM
**Cause :** `ENCRYPTION_KEY` manquante ou format incorrect.
**Solution :** La clé doit être en base64 (32 bytes = 44 chars en base64).
```bash
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### Données affichées comme bytes bruts
**Cause :** Déchiffrement échoué (mauvaise clé ou données corrompues).
**Solution :**
1. Vérifier que `ENCRYPTION_KEY` n'a pas changé depuis l'insertion.
2. Ne jamais changer `ENCRYPTION_KEY` en production sans re-chiffrer les données.

---

## Erreurs courantes API

### `422 Unprocessable Entity`
Validation Pydantic échouée. Lire le champ `detail` de la réponse pour identifier le champ invalide.

### `429 Too Many Requests`
Rate limiting Redis déclenché. Attendre 60 secondes ou augmenter `RATE_LIMIT_PER_MINUTE` en dev.

### `500 Internal Server Error` — Debug
```bash
# Activer les logs détaillés
APP_DEBUG=true uvicorn src.main:app --reload

# Voir les logs Sentry
# https://sentry.io/organizations/servantassist/

# Reproduire localement
curl -X GET http://localhost:8000/api/v1/endpoint -H "Authorization: Bearer $TOKEN"
```

---

## Performance

### Requêtes lentes
```bash
# Activer EXPLAIN ANALYZE sur les requêtes lentes
# Chercher les N+1 dans les repositories (utiliser joinedload)
```

### Mémoire Redis croissante
```bash
redis-cli INFO memory
redis-cli DBSIZE  # Nombre de clés

# Nettoyer les tokens expirés (ils ont un TTL automatique)
# Si mémoire > 500MB, vérifier les listes de jobs Celery
```

---

## Procédure de rollback d'urgence

```bash
# 1. Arrêter le trafic (mettre en maintenance)
# 2. Backup DB
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Rollback migration
alembic downgrade -1

# 4. Redéployer la version précédente
git checkout <previous-tag>
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app

# 5. Vérifier la santé
curl http://localhost:8000/health
```
