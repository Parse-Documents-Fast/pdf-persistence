from motor.motor_asyncio import AsyncIOMotorDatabase

from pdf_persistence.models import (
    PersistCreateRequest,
    PersistRecord,
    PersistUpdateRequest,
)
from pdf_persistence.repository import (
    create_document as repo_create_document,
)
from pdf_persistence.repository import (
    delete_document as repo_delete_document,
)
from pdf_persistence.repository import (
    get_document_by_checksum as repo_get_document_by_checksum,
)
from pdf_persistence.repository import (
    get_document_by_id as repo_get_document_by_id,
)
from pdf_persistence.repository import (
    list_documents as repo_list_documents,
)
from pdf_persistence.repository import (
    update_document as repo_update_document,
)


async def create_document(
    db: AsyncIOMotorDatabase, request: PersistCreateRequest
) -> PersistRecord:
    return await repo_create_document(db, request)


async def get_document(db: AsyncIOMotorDatabase, document_id: str) -> PersistRecord:
    return await repo_get_document_by_id(db, document_id)


async def get_document_by_checksum(
    db: AsyncIOMotorDatabase, checksum: str
) -> PersistRecord | None:
    return await repo_get_document_by_checksum(db, checksum)


async def update_document(
    db: AsyncIOMotorDatabase, document_id: str, request: PersistUpdateRequest
) -> PersistRecord:
    return await repo_update_document(db, document_id, request)


async def list_documents(
    db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
) -> list[PersistRecord]:
    return await repo_list_documents(db, skip=skip, limit=limit)


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    return await repo_delete_document(db, document_id)
