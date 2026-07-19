from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config

SYNC_DATABASE_URL = Config.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
)

engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_session():
    return SessionLocal()