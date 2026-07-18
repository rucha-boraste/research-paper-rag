from fastapi import APIRouter, UploadFile, File, Depends, status, HTTPException

from uuid import UUID

from app.database import async_session_local
from app.rag.service import upload_document, query_documents, answer_query, get_user_chat, get_user_documents, get_document_status
from app.rag.schemas import DocumentResponse, QueryRequest, QueryResponse, AnswerResponse, ChatHistoryResponse, UploadDocumentResponse, AnswerRequest, DocumentStatusResponse

from app.celery.tasks import process_document_task

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

        try:
            process_document_task.delay(str(document.id))

            document.status = "QUEUED"
            await session.commit()
            await session.refresh(document)

        except Exception:
            document.status = "FAILED"
            document.error_message = "Failed to queue processing task."
            await session.commit()
            raise
    
    return {
        "message": "Document uploaded successfully.",
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
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
    
@rag_router.get(
    "/documents/{document_id}/status",
    response_model=DocumentStatusResponse,
)
async def get_status(document_id: UUID):
    async with async_session_local() as session:

        document = await get_document_status(
            document_id=document_id,
            session=session,
        )

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

        return DocumentStatusResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            processed_at=document.processed_at,
            error_message=document.error_message,
        )