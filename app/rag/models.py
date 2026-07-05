from sqlmodel import SQLModel, Field, Column
import  sqlalchemy.dialects.postgresql as pg
import uuid
from datetime import datetime

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