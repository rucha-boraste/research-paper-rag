from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import initdb
from app.rag.router import rag_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting")
    await initdb()
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

