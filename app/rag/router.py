from fastapi import APIRouter, UploadFile, File

from app.database import async_session_local
from app.rag.service import upload_document, process_document
from app.rag.schemas import DocumentResponse, DocumentChunksResponse, ChunkResponse

rag_router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

@rag_router.post("/upload",response_model=DocumentChunksResponse)
async def upload_pdf(file: UploadFile = File(...),):
    async with async_session_local() as session:
        document = await upload_document(
            file,
            session
        )
    
        chunks = await process_document(
            document,
            session
        )
    
    return {
        "id": document.id,
        "filename": document.filename,
        "uploaded_at": document.uploaded_at,
        "chunks": chunks,
    }