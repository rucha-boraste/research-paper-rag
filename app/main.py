from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import initdb
from app.rag.router import rag_router
from app.rag.vectorstore import init_vector_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting")
    await initdb()
    init_vector_store()
    yield
    print("Server is stopping")

app = FastAPI(
    lifespan=lifespan
)

app.include_router(rag_router)
# @app.get("/")
# async def root():
#     return {
#         "message" : "I am unstopable"
#     }

