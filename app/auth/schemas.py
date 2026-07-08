from sqlmodel import SQLModel
from uuid import UUID
import datetime

class UserCreateModel(SQLModel):
    username: str
    email: str
    password: str

class UserResponseModel(SQLModel):
    id: UUID
    username: str
    email: str
    is_verified: bool
    created_at: datetime.datetime

class UserLoginModel(SQLModel):
    email: str
    password: str