from uuid import UUID

from .celery_app import celery_app
from app.rag.processor import process_document


@celery_app.task(name="process_document")
def process_document_task(document_id: str):
    process_document(UUID(document_id))