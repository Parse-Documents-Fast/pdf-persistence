from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from pdf_persistence.db import get_db
from pdf_persistence.services import (
    create_document,
    delete_document,
    get_document,
    get_document_by_checksum,
    list_documents,
    update_document,
)
from pdf_persistence.models import PersistCreateRequest, PersistRecord, PersistUpdateRequest
from pdf_persistence.rfc9457 import DocumentNotFoundException

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=PersistRecord, status_code=status.HTTP_201_CREATED)
async def create_document_endpoint(
    request: PersistCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PersistRecord:
    return await create_document(db, request)

@router.get("/by-checksum", response_model=PersistRecord)
async def get_document_by_checksum_endpoint(
    checksum: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PersistRecord:
    record = await get_document_by_checksum(db, checksum)
    if not record:
        raise DocumentNotFoundException(document_id=f"checksum:{checksum}")
    return record

@router.get("/{document_id}", response_model=PersistRecord)
async def get_document_endpoint(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PersistRecord:
    return await get_document(db, document_id)

@router.patch("/{document_id}", response_model=PersistRecord)
async def update_document_endpoint(
    document_id: str,
    request: PersistUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PersistRecord:
    return await update_document(db, document_id, request)

@router.get("", response_model=list[PersistRecord])
async def list_documents_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[PersistRecord]:
    return await list_documents(db, skip=skip, limit=limit)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Response:
    deleted = await delete_document(db, document_id)
    if not deleted:
        raise DocumentNotFoundException(document_id=document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
