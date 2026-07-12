import asyncio
import traceback
from uuid import UUID

from sqlmodel import select

from app.celery_app import celery
from app.database import async_session_local
from app.rag.models import Document
from app.rag.service import process_document


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_document_task(self, document_id: str):

    async def runner():

        async with async_session_local() as session:

            statement = select(Document).where(
                Document.id == UUID(document_id)
            )

            result = await session.execute(statement)

            document = result.scalar_one_or_none()

            if document is None:
                return

            document.status = "processing"

            await session.commit()

            try:
                print("Started processing:", document.filename)
                await process_document(
                    document,
                    session,
                )
                print("Finished process_document()")

                document.status = "completed"

                await session.commit()
                print("Status updated to completed")
            except Exception:

                traceback.print_exc()

                document.status = "failed"

                await session.commit()

                raise

    asyncio.run(runner())