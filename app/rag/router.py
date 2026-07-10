from fastapi import APIRouter, UploadFile, File, Depends

from app.database import async_session_local
from app.rag.service import upload_document, process_document, query_documents, answer_query, get_user_chat
from app.rag.schemas import DocumentChunksResponse, QueryRequest, QueryResponse, AnswerResponse, ChatHistoryResponse

from app.auth.dependency import AccessTokenBearer

access_token_bearer = AccessTokenBearer()

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

@rag_router.post("/answer", response_model=AnswerResponse)
async def answer_pdf(query: QueryRequest):
    return await answer_query(query.query)

@rag_router.get("/get_history", response_model=ChatHistoryResponse)
async def get_chats(user=Depends(access_token_bearer)):
    async with async_session_local() as session:
        chats = await get_user_chat(
            user_id=user["user_uid"],
            session=session,
        )

        return ChatHistoryResponse(chats=chats)