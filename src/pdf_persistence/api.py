from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from pdf_persistence.db import get_db
from pdf_persistence.services import (
    delete_document,
    get_document,
    list_documents,
    process_and_save_pdf,
)
from pdf_persistence.models import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document_endpoint(
    title: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, str]:
    """Uploads a PDF, parses it, and saves it to the database."""
    file_bytes = await file.read()
    document_id, _, _ = await process_and_save_pdf(db, file_bytes, title)
    return {"id": document_id}

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_endpoint(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DocumentResponse:
    """Retrieves a document by its ID."""
    return await get_document(db, document_id)


@router.get("", response_model=list[DocumentResponse])
async def list_documents_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[DocumentResponse]:
    """Lists documents with pagination."""
    return await list_documents(db, skip=skip, limit=limit)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Response:
    """Deletes a document by its ID."""
    deleted = await delete_document(db, document_id)
    if not deleted:
        # If it was not deleted, it means it was not found, but standard REST
        # delete operations might just return 204 regardless or 404.
        # We will return a 404 using the domain exception.
        from pdf_persistence.rfc9457 import DocumentNotFoundException
        raise DocumentNotFoundException(document_id=document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
