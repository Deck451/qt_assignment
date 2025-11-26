"""Fetching CIK data Celery task definition module."""

from app.lib.sync_storage import run
from worker.celery import celery


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def run_task(self):
    """Fetch CIK data Celery task."""
    try:
        run()
    except Exception as exc:
        raise self.retry(exc=exc)
