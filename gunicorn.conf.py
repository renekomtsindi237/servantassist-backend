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
# preload_app=True : charge l'app une fois dans le master, les workers forkent
# → économise RAM (copy-on-write) et accélère le redémarrage des workers
preload_app = True

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

def post_fork(server, worker):
    # Réinitialise le pool de connexions SQLAlchemy dans chaque worker
    # (évite de partager des connexions DB entre processus après le fork)
    try:
        from src.infrastructure.database.session import sessionmanager
        if sessionmanager._engine is not None:
            import asyncio
            asyncio.get_event_loop().run_until_complete(sessionmanager.close())
            from src.infrastructure.database.session import (
                DatabaseSessionManager,
                _build_engine_kwargs,
                get_db_url,
            )
            sessionmanager._engine = None
            # Le manager se réinitialisera à la première requête
    except Exception:
        pass

def worker_exit(server, worker):
    server.log.info("Worker %s arrêté proprement", worker.pid)
