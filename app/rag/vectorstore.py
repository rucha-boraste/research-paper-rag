from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config import Config

embeddings_model = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=Config.HUGGINGFACEHUB_API_TOKEN,
)

vector_store: PGVector | None = None


def init_vector_store():
    global vector_store

    if vector_store is None:
        vector_store = PGVector(
            embeddings=embeddings_model,
            collection_name="embeddings",
            connection=Config.PGVECTOR_CONNECTION,
            create_extension=False,
            engine_args={
                "echo": False,
                "connect_args": {
                    "prepare_threshold": 0,
                }
            },
        )

def get_vector_store() -> PGVector:
    global vector_store

    if vector_store is None:
        init_vector_store()

    if vector_store is None:
        raise RuntimeError("Vector store has not been initialized.")

    return vector_store