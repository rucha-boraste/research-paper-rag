from celery import Celery

celery_app = Celery(
    "rag_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["app.celery.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)