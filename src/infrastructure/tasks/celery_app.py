"""
Configuration Celery pour les tâches planifiées.

Worker : celery -A src.infrastructure.tasks.celery_app worker --loglevel=info
Beat   : celery -A src.infrastructure.tasks.celery_app beat --loglevel=info
Flower : celery -A src.infrastructure.tasks.celery_app flower --port=5555

Schedule des tâches planifiées :
  - send_event_reminders  : chaque matin à 8h00 (rappels 24h avant un événement)
  - send_weekly_report    : chaque lundi à 7h00 (rapport hebdomadaire aux admins)
  - cleanup_notifications : chaque nuit à 2h00 (purge des notifications lues +30j)
"""
import os

from celery import Celery
from celery.schedules import crontab

# Charger les variables d'environnement si non déjà chargées
_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "servantassist",
    broker=_redis_url,
    backend=_redis_url,
    include=["src.infrastructure.tasks.scheduled"],
)

celery_app.conf.update(
    # Sérialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Douala",
    enable_utc=True,
    # Résultats — conserver 24h
    result_expires=86400,
    # Retry automatique sur perte de connexion broker
    broker_connection_retry_on_startup=True,
    # Schedule Beat
    beat_schedule={
        "send-event-reminders": {
            "task": "src.infrastructure.tasks.scheduled.send_event_reminders",
            "schedule": crontab(hour=8, minute=0),
            "options": {"queue": "default"},
        },
        "send-weekly-report": {
            "task": "src.infrastructure.tasks.scheduled.send_weekly_report",
            "schedule": crontab(hour=7, minute=0, day_of_week="monday"),
            "options": {"queue": "default"},
        },
        "cleanup-notifications": {
            "task": "src.infrastructure.tasks.scheduled.cleanup_notifications",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "default"},
        },
    },
)
