from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel
from typing import Any

class UploadDocumentResponse(SQLModel):
    message: str
    document_id: UUID
    filename: str
    status: str

class DocumentResponse(SQLModel):
    id: UUID
    filename: str
    uploaded_at: datetime

class ChunkResponse(SQLModel):
    document_id: UUID
    chunk_index: int
    chunk_id: str
    content: str
    meta_data: dict[str, Any]
    start_index: int | None = None
    page_index: int | None = None
    section_title: str | None = None

class DocumentChunksResponse(SQLModel):
    id: UUID
    filename: str
    uploaded_at: datetime
    chunks: list[ChunkResponse]

class QueryRequest(SQLModel):
    query: str

class RetrievedChunkedResponse(SQLModel):
    chunk_id: str
    content: str
    document_id: UUID
    chunk_index:int
    page_number: int | None = None
    section_title: str | None = None
    score: float | None = None

class QueryResponse(SQLModel):
    query: str
    results: list[RetrievedChunkedResponse]

class AnswerResponse(SQLModel):
    query: str
    answer: str

class AnswerRequest(SQLModel):
    query: str
    document_id: UUID
    
class ChatResponse(SQLModel):
    id: UUID
    question: str
    answer: str
    document_id: UUID
    created_at: datetime

class ChatHistoryResponse(SQLModel):
    chats: list[ChatResponse]

class DocumentStatusResponse(SQLModel):
    document_id: UUID
    filename: str
    status: str
    processed_at: datetime | None = None
    error_message: str | None = None    