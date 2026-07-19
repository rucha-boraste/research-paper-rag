from uuid import UUID

from .celery_app import celery_app
from app.rag.processor import process_document
import os
from datetime import datetime

@celery_app.task(name="process_document")
def process_document_task(document_id: str):
    print(
        f"START {document_id} | PID={os.getpid()} | {datetime.now().strftime('%H:%M:%S')}"
    )

    process_document(UUID(document_id))

    print(
        f"END   {document_id} | PID={os.getpid()} | {datetime.now().strftime('%H:%M:%S')}"
    )
    