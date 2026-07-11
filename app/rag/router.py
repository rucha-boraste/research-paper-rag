from fastapi import APIRouter, UploadFile, File, Depends, status

from uuid import UUID

from app.database import async_session_local
from app.rag.service import upload_document, process_document, query_documents, answer_query, get_user_chat, get_user_documents
from app.rag.schemas import DocumentResponse, QueryRequest, QueryResponse, AnswerResponse, ChatHistoryResponse, UploadDocumentResponse, AnswerRequest

from app.auth.dependency import AccessTokenBearer

access_token_bearer = AccessTokenBearer()

rag_router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

@rag_router.post("/upload", response_model=UploadDocumentResponse, status_code=status.HTTP_201_CREATED )
async def upload_pdf(file: UploadFile = File(...),user=Depends(access_token_bearer)):
    async with async_session_local() as session:
        document = await upload_document(
            file,
            session,
            user_id=user["user_uid"],
        )
    
        await process_document(
            document,
            session
        )
    
    return {
        "message": "Document uploaded successfully.",
        "document_id": document.id,
        "filename": document.filename,
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
async def answer_pdf(payload: AnswerRequest, user=Depends(access_token_bearer)):
    async with async_session_local() as session:
        return await answer_query(
            query=payload.query,
            user_id=user["user_uid"],
            document_id=payload.document_id,
            session=session,
        )

@rag_router.get("/get_history", response_model=ChatHistoryResponse)
async def get_chats(document_id: UUID, user=Depends(access_token_bearer)):
    async with async_session_local() as session:
        chats = await get_user_chat(
            user_id=user["user_uid"],
            document_id=document_id,
            session=session,
        )

        return ChatHistoryResponse(chats=chats)
    
@rag_router.get("/get_documents", response_model= list[DocumentResponse])
async def get_docs(user=Depends(access_token_bearer)):
    async with async_session_local() as session:
        documents = await get_user_documents(
            user_id=user["user_uid"],
            session=session
        )

        return documents