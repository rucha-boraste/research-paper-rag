from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel
from typing import Any

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