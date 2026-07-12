from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from tempfile import NamedTemporaryFile
from uuid import uuid4
from uuid import UUID
import asyncio

import re
from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument #just an alias name to avoid nameclash with Document class
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.rag.models import Document, Chunk, ChatHistory
from app.rag.storage import supabase
from app.rag.vectorstore import get_vector_store, embeddings_model
from app.rag.schemas import ChatResponse

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
    
LOW_SIGNAL_PATTERNS = [
    r"^references?$",
    r"^bibliography$",
    r"^acknowledg(e|ements?)?$",
    r"^author(s)?$",
    r"^abstract$",
    r"^keywords?$",
]

CITATION_PATTERNS = [
    r"\bdoi:\s*",
    r"\barxiv\b",
    r"\burl\s*https?://",
    r"\bet al\.\b",
    r"\[[0-9]+\]",
    r"\bproceedings\b",
    r"\bconference\b",
]

def clean_chunk_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(
        r"(?im)^(references|bibliography|acknowledgements?)\s*$",
        "",
        text,
    )
    text = re.sub(r"\b(figure|table|equation)\s*[0-9A-Za-z.-]+\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_low_signal(chunk_text: str) -> bool:
    if not chunk_text:
        return True
    lower = chunk_text.lower()
    if len(chunk_text.split()) < 8:
        return True
    if any(re.search(pattern, lower) for pattern in LOW_SIGNAL_PATTERNS):
        return True
    if sum(1 for pattern in CITATION_PATTERNS if re.search(pattern, lower)) >= 2:
        return True
    return False

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


async def process_document(document: Document, session: AsyncSession):

    '''
    Load document and convert into chunks
    '''

    storage_path = f"{document.id}.pdf"

    pdf_bytes = supabase.storage.from_("documents").download(storage_path)

    with NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()

        loader = UnstructuredLoader(
            file_path=tmp.name,
            partition_via_api=True,
            strategy="hi_res",
            chunking_strategy="by_title",
            max_characters=900,
            new_after_n_chars=700,
            overlap=120,
        )

        docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=120,
    )

    chunks = []
    for doc in docs:
        if len(doc.page_content) > 1200:
            chunks.extend(text_splitter.split_documents([doc]))
        else:
            chunks.append(doc)

    filtered_chunks = []
    seen = set()

    for idx, chunk in enumerate(chunks):
        cleaned = clean_chunk_text(chunk.page_content)
        if is_low_signal(cleaned):
            continue

        key = cleaned.lower()
        
        if key in seen:
            continue

        seen.add(key)

        metadata = dict(chunk.metadata or {})
        chunk_id = str(uuid4())

        chunk_record = Chunk(
            document_id=document.id,
            chunk_index=len(filtered_chunks),
            chunk_id=chunk_id,
            content=cleaned,
            meta_data={
                **metadata,

                "document_id": str(document.id),
                "document_name": document.filename,

                "chunk_id": chunk_id,
                "chunk_index": len(filtered_chunks),

                "page_number": metadata.get("page_number"),
                "start_index": metadata.get("start_index"),

                "section_title": (
                    metadata.get("section_title")
                    or metadata.get("parent_title")
                    or metadata.get("title")
                    or "Unknown"
                ),

                "element_type": metadata.get("category"),
            },
            start_index=metadata.get("start_index"),
            page_number=metadata.get("page_number"),
            section_title=(
                metadata.get("section_title")
                or metadata.get("parent_title")
                or metadata.get("title")
                or "Unknown"
            ),
        )
        filtered_chunks.append(chunk_record)

    if filtered_chunks:
        session.add_all(filtered_chunks)
        await session.commit()
        for chunk in filtered_chunks:
            await session.refresh(chunk)
            
        vector_store = get_vector_store()
        vector_documents = []

        for chunk in filtered_chunks:
            enriched_content = f"""
        Document: {document.filename}

        Section: {chunk.section_title or "Unknown"}

        Page: {chunk.page_number or "Unknown"}

        {chunk.content}
        """.strip()

            vector_documents.append(
                LCDocument(
                    page_content=enriched_content,
                    metadata={
                        "document_id": str(chunk.document_id),
                        "document_name": document.filename,

                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,

                        "page_number": chunk.page_number,
                        "start_index": chunk.start_index,

                        "section_title": chunk.section_title,
                    },
                )
            )
        vector_ids = [chunk.id for chunk in filtered_chunks]

        await asyncio.to_thread(
            vector_store.add_documents,
            documents=vector_documents,
            ids=vector_ids,
        )

    return filtered_chunks


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