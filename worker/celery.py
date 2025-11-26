"""Celery app module."""

# pylint: disable=cyclic-import

import os

from celery import Celery
from celery.schedules import crontab


celery: Celery = Celery(
    "tasks",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):  # pylint: disable=unused-argument
    """Setup Celery tasks to run on a schedule."""
    import app.tasks.refresh_cik_data  # pylint: disable=import-outside-toplevel

    sender.add_periodic_task(
        schedule=crontab(
            hour=6,
        ),
        sig=app.tasks.refresh_cik_data.run_task.s(),
        name="refresh CIK data",
    )
