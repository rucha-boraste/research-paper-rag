from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel

class DocumentResponse(SQLModel):
    id: UUID
    filename: str
    uploaded_at: datetime