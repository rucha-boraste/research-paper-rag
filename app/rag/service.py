from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import uuid4
from uuid import UUID
import asyncio

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.rag.models import Document, ChatHistory
from app.rag.storage import supabase
from app.rag.vectorstore import get_vector_store, embeddings_model
from app.rag.schemas import ChatResponse

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

async def upload_document(file: UploadFile, session: AsyncSession, user_id: uuid4):

    '''
    Store document metadata in 'documents' table and document in storage
    '''

    document = Document(
        user_id=user_id,
        filename=file.filename,
    )

    session.add(document)

    await session.commit()
    await session.refresh(document)

    contents = await file.read()

    supabase.storage.from_("documents").upload(
        path=f"{document.id}.pdf",
        file=contents,
        file_options={
            "content-type": "application/pdf"
        },
    )

    return document


async def query_documents(query: str, document_id: uuid4, k: int = 8):
    print("Inside service")
    vector_store = get_vector_store()
    print("Got vector store")
    
    print("Embedding user query")

    embedding = embeddings_model.embed_query(query)
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"

    stmt = text(
        """
        SELECT
        document,
        cmetadata,
        embedding <=> CAST(:embedding AS vector) AS distance
        FROM langchain_pg_embedding
        WHERE cmetadata->>'document_id' = :document_id
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :k;
        """
    )

    with vector_store._engine.connect() as conn:
        rows = conn.execute(
            stmt,
            {
                "embedding": embedding_str,
                "document_id": str(document_id),
                "k": k,
            },
        ).fetchall()

    results = []

    for row in rows:
        results.append(
            {
                "chunk_id": row.cmetadata.get("chunk_id"),
                "content": row.document,
                "document_id": row.cmetadata.get("document_id"),
                "chunk_index": row.cmetadata.get("chunk_index"),
                "page_number": row.cmetadata.get("page_number"),
                "section_title": row.cmetadata.get("section_title"),
                "score": float(row.distance),
            }
        )

    print(f"Retrieved {len(results)} chunks")

    return results

PROMPT = ChatPromptTemplate.from_template("""
You are an expert assistant answering questions about ONE research paper.

Use ONLY the retrieved context.

Instructions:

- Combine information across multiple retrieved chunks whenever necessary.
- Prefer evidence from the Abstract, Introduction, Contributions and Conclusion sections.
- If multiple chunks contain overlapping information, synthesize them into one coherent answer.
- Do NOT invent information.
- If the retrieved context is insufficient, reply exactly:

"The retrieved context does not contain enough information to answer this question."

Retrieved Context:
{context}

Question:
{input}

Provide a concise but complete answer.
""")

def format_retrieved_chunks(chunks: list[dict]) -> str:
    formatted = []

    for i, chunk in enumerate(chunks, start=1):
        formatted.append(
                f"""
    ========== Chunk {i} ==========

    Document: {chunk.get("document_id")}
    Section: {chunk.get("section_title")}
    Page: {chunk.get("page_number")}
    Similarity Score: {chunk.get("score")}

    Content:
    {chunk.get("content")}
    """
            )

    return "\n\n".join(formatted)

async def answer_query(query: str,user_id: uuid4, document_id: uuid4, session: AsyncSession, k: int = 8):
    retrieved_chunks = await query_documents(query, document_id=document_id, k=k)
    # print("=" * 80)
    # for i, chunk in enumerate(retrieved_chunks):
    #     print(f"\nChunk {i}")
    #     print("Section:", chunk.get("section_title"))
    #     print("Page:", chunk.get("page_number"))
    #     print(chunk["content"][:500])
    # print("=" * 80)
    context = format_retrieved_chunks(retrieved_chunks)

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
    )

    chain = PROMPT | llm
    response = await asyncio.to_thread(
        chain.invoke,
        {"context": context, "input": query},
    )

    answer = response.content if hasattr(response, "content") else str(response)

    chat = ChatHistory(
        user_id=user_id,
        document_id=document_id,
        question=query,
        answer=answer,
    )

    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    return {
        "query": query,
        "answer": answer,
    }


async def get_user_chat(user_id: UUID, document_id: UUID, session: AsyncSession):
    statement = (
        select(ChatHistory)
        .where(
            ChatHistory.user_id == user_id,
            ChatHistory.document_id == document_id,
        )
        .order_by(ChatHistory.created_at.desc())
    )

    result = await session.execute(statement)

    chats = result.scalars().all()

    if chats:
        return [
            ChatResponse(
                id=chat.id,
                question=chat.question,
                answer=chat.answer,
                document_id=chat.document_id,
                created_at=chat.created_at,
            )
            for chat in chats
        ]
    else:
        return []


async def get_user_documents(user_id: uuid4, session: AsyncSession):
    statement = select(Document).where(Document.user_id == user_id).order_by(Document.uploaded_at.desc())
    result = await session.execute(statement)
    return result.scalars().all()


async def get_document_status(document_id: UUID,session: AsyncSession,) -> Document | None:

    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )

    return result.scalar_one_or_none()