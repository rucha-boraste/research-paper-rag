from fastapi import APIRouter, UploadFile, File

from app.database import async_session_local
from app.rag.service import upload_document
from app.rag.schemas import DocumentResponse

rag_router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

@rag_router.post("/upload",response_model=DocumentResponse)
async def upload_pdf(file: UploadFile = File(...),):
    async with async_session_local() as session:
        document = await upload_document(
            file,
            session
        )
    
    return document