"""
Gunicorn configuration — ServantAssist Backend
Workers dynamiques basés sur les CPU disponibles.
"""
import multiprocessing
import os

# ── Workers ────────────────────────────────────────────────────────────────
# Formule standard : 2 × CPU + 1
# Plafonné à 8 pour ne pas saturer le pool Supabase pgbouncer
_cpu = multiprocessing.cpu_count()
workers = int(os.environ.get("GUNICORN_WORKERS", min(2 * _cpu + 1, 8)))

worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# ── Réseau ─────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('APP_PORT', '8000')}"
backlog = 2048

# ── Timeouts ───────────────────────────────────────────────────────────────
timeout = 120          # Tue un worker bloqué après 120s
graceful_timeout = 30  # Laisse 30s aux requêtes en cours lors d'un SIGTERM
keepalive = 5

# ── Mémoire ────────────────────────────────────────────────────────────────
# preload_app=False : chaque worker charge l'app indépendamment après le fork
# → évite de partager l'état asyncio/asyncpg/sessionmanager entre processus

# Recyclage des workers pour éviter les fuites mémoire à long terme
max_requests = 1000
max_requests_jitter = 100  # Décale les redémarrages pour éviter un pic simultané

# ── Logging ────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = (
    '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs worker=%(p)s'
)

# ── Hooks lifecycle ────────────────────────────────────────────────────────
def on_starting(server):
    server.log.info(
        "ServantAssist démarrage : %d worker(s) sur %d CPU",
        workers, _cpu
    )

def worker_exit(server, worker):
    server.log.info("Worker %s arrêté proprement", worker.pid)
