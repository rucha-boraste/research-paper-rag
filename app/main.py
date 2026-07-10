from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.database import initdb
from app.rag.router import rag_router
from app.rag.vectorstore import init_vector_store
from app.auth.router import auth_router

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

origins = [
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "/api/v1"

app.include_router(rag_router, prefix=API_VERSION)
app.include_router(auth_router, prefix=API_VERSION)
# @app.get("/")
# async def root():
#     return {
#         "message" : "I am unstopable"
#     }

