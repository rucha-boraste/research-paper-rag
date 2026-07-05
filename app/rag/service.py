from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.models import Document
from app.rag.storage import supabase

async def upload_document(file: UploadFile, session: AsyncSession):

    document = Document(
        filename=file.filename,
    )

    session.add(document)

    await session.commit()
    await session.refresh(document)

    contents = await file.read()

    supabase.storage.from_("documents").upload(
        path=f"{document.id}.pdf",
        file=contents,
        file_options={
            "content-type": "application/pdf"
        },
    )

    return document