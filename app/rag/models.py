from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import ForeignKey
import sqlalchemy.dialects.postgresql as pg
import uuid
from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        )
    )
    filename: str
    uploaded_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            default=datetime.now
        )
    )

    def __repr__(self) -> str:
        return f"<Document {self.filename}>"
    

class Chunk(SQLModel, table=True):
    
    __tablename__ = "chunks"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        )
    )
    document_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    chunk_index: int = Field(nullable=False, index=True)
    chunk_id: str = Field(nullable=False, unique=True, index=True)
    content: str = Field(nullable=False)

    meta_data: dict[str, Any] =Field(
        default_factory=dict,
        sa_column=Column(
            pg.JSONB,
            nullable=False
        )
    )
    start_index: Optional[int] = Field(default=None)
    page_number: Optional[int] = Field(default=None)
    section_title: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            default=datetime.now
        )
    )

    def __repr__(self) -> str:
        return f"<Chunk document_id={self.document_id} chunk_index={self.chunk_index}>" 
    
