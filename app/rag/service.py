from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from tempfile import NamedTemporaryFile
from uuid import uuid4

import re
from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.models import Document, Chunk
from app.rag.storage import supabase

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
        r"(?i)\b(author|authors|references|bibliography|acknowledg(e|ements?))\b.*",
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
    if len(chunk_text.split()) < 25:
        return True
    if any(re.search(pattern, lower) for pattern in LOW_SIGNAL_PATTERNS):
        return True
    if sum(1 for pattern in CITATION_PATTERNS if re.search(pattern, lower)) >= 2:
        return True
    return False


async def upload_document(file: UploadFile, session: AsyncSession):

    '''
    Store document metadata in 'documents' table and document in storage
    '''

    document = Document(
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
            strategy="fast",
            chunking_strategy="by_title",
            max_characters=800,
            new_after_n_chars=600,
            overlap=50,
        )

        docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        add_start_index=True,
    )

    chunks = text_splitter.split_documents(docs)

    filtered_chunks = []
    seen = set()

    for idx, chunk in enumerate(chunks):
        cleaned = clean_chunk_text(chunk.page_content)
        if is_low_signal(cleaned):
            continue

        key = cleaned.lower()
        if len(key) < 80:
            continue
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
                "chunk_id": chunk_id,
                "chunk_index": len(filtered_chunks),
                "filename": document.filename,
            },
            start_index=metadata.get("start_index"),
            page_number=metadata.get("page_number"),
            section_title=metadata.get("section_title") or metadata.get("category"),
        )
        filtered_chunks.append(chunk_record)

    if filtered_chunks:
            session.add_all(filtered_chunks)
            await session.commit()
            for chunk in filtered_chunks:
                await session.refresh(chunk)

    return filtered_chunks

