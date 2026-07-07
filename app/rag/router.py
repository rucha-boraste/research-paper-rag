from fastapi import APIRouter, UploadFile, File

from app.database import async_session_local
from app.rag.service import upload_document, process_document, query_documents
from app.rag.schemas import DocumentChunksResponse, QueryRequest, QueryResponse

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

@rag_router.post("/query", response_model=QueryResponse)
async def query_pdf(query: QueryRequest):
    print("Received query:", query.query)
    results = await query_documents(query.query)
    return{
        "query": query.query,
        "results": results,
    }