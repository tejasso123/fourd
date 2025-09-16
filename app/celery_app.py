from celery import Celery
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


def make_celery():
    redis_url = os.getenv("REDIS_URL")

    celery_app = Celery(
        "app",
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks.file_tasks"],  # Explicitly include tasks
    )

    # celery_app.conf.update(
    #     task_routes={
    #         "app.tasks.*": {"queue": "default"},
    #     },
    #     task_serializer="json",
    #     result_serializer="json",
    #     accept_content=["json"],
    #     timezone="UTC",
    #     enable_utc=True,
    # )

    return celery_app


# celery_app = make_celery()
mk_celery = make_celery()
