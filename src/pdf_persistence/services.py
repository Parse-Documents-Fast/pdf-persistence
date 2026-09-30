import hashlib

import fitz  # PyMuPDF
import pymupdf4llm
from motor.motor_asyncio import AsyncIOMotorDatabase

from pdf_persistence.models import DocumentCreate, DocumentResponse
from pdf_persistence.repository import (
    create_document,
    get_document_by_checksum,
    get_document_by_id,
)
from pdf_persistence.repository import (
    delete_document as repo_delete_document,
)
from pdf_persistence.repository import (
    list_documents as repo_list_documents,
)
from pdf_persistence.rfc9457 import DuplicateDocumentException


async def process_and_save_pdf(db: AsyncIOMotorDatabase, file_bytes: bytes, title: str) -> str:
    """
    Parses a PDF into Markdown and saves it to the database if it's not a duplicate.
    Returns the ID of the inserted document.
    """
    # 1. Generate checksum
    checksum = hashlib.sha256(file_bytes).hexdigest()
    
    # 2. Check for duplicate
    existing_doc = await get_document_by_checksum(db, checksum)
    if existing_doc:
        raise DuplicateDocumentException(checksum=checksum)
    
    # 3. Parse PDF with pymupdf4llm
    # We use stream to parse from bytes without saving to disk
    doc_fitz = fitz.Document(stream=file_bytes, filetype="pdf")
    md_text = pymupdf4llm.to_markdown(doc_fitz)
    
    # 4. Create payload and save
    payload = DocumentCreate(
        content=md_text,
        checksum=checksum,
        title=title,
    )
    
    document_id = await create_document(db, payload)
    return document_id


async def get_document(db: AsyncIOMotorDatabase, document_id: str) -> DocumentResponse:
    """
    Delegates to the repository to retrieve a document by ID.
    """
    return await get_document_by_id(db, document_id)


async def list_documents(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100) -> list[DocumentResponse]:
    """
    Delegates to the repository to list documents.
    """
    return await repo_list_documents(db, skip=skip, limit=limit)


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    """
    Delegates to the repository to delete a document.
    """
    return await repo_delete_document(db, document_id)
