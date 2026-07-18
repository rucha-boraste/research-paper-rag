from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4
import re

from sqlalchemy import select
from datetime import datetime, timezone

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader

from app.database_sync import get_session
from app.rag.models import Document, Chunk
from app.auth.models import User
from app.rag.storage import supabase
from app.rag.vectorstore import get_vector_store

from app.config import Config

from dotenv import load_dotenv
load_dotenv()

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

    text = re.sub(
        r"\b(figure|table|equation)\s*[0-9A-Za-z.-]+\b",
        "",
        text,
    )

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

    if sum(
        1
        for pattern in CITATION_PATTERNS
        if re.search(pattern, lower)
    ) >= 2:
        return True

    return False


def process_document(document_id: UUID):

    with get_session() as session:

        result = session.execute(
            select(Document).where(
                Document.id == document_id
            )
        )

        document = result.scalar_one_or_none()

        if document is None:
            return

        document.status = "PROCESSING"
        session.commit()

        try:

            storage_path = f"{document.id}.pdf"

            pdf_bytes = (
                supabase.storage
                .from_("documents")
                .download(storage_path)
            )

            with NamedTemporaryFile(
                suffix=".pdf",
                delete=True,
            ) as tmp:

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

                    chunks.extend(
                        text_splitter.split_documents([doc])
                    )

                else:

                    chunks.append(doc)

            filtered_chunks = []

            seen = set()

            for chunk in chunks:

                cleaned = clean_chunk_text(
                    chunk.page_content
                )

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

                    start_index=metadata.get(
                        "start_index"
                    ),

                    page_number=metadata.get(
                        "page_number"
                    ),

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
                session.commit()

                for chunk in filtered_chunks:
                    session.refresh(chunk)

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

                vector_ids = [
                    str(chunk.id)
                    for chunk in filtered_chunks
                ]

                vector_store.add_documents(
                    documents=vector_documents,
                    ids=vector_ids,
                )

            document.status = "COMPLETED"
            document.processed_at = datetime.now(timezone.utc)
            document.error_message = None

            session.commit()

            return filtered_chunks

        except Exception as e:

            session.rollback()

            document.status = "FAILED"
            document.error_message = str(e)

            session.commit()

            raise