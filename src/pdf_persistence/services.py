import logging

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

logger = logging.getLogger(__name__)


async def create_document(
    db: AsyncIOMotorDatabase, request: PersistCreateRequest
) -> PersistRecord:
    record = await repo_create_document(db, request)
    logger.info(
        "document created",
        extra={
            "fields": {
                "pdf_id": str(record.id),
                "checksum": record.checksum,
                "original_format": record.original_format,
                "status": record.status,
            }
        },
    )
    return record


async def get_document(db: AsyncIOMotorDatabase, document_id: str) -> PersistRecord:
    record = await repo_get_document_by_id(db, document_id)
    logger.debug(
        "document retrieved",
        extra={"fields": {"pdf_id": document_id}},
    )
    return record


async def get_document_by_checksum(
    db: AsyncIOMotorDatabase, checksum: str
) -> PersistRecord | None:
    record = await repo_get_document_by_checksum(db, checksum)
    if record:
        logger.debug(
            "document found by checksum",
            extra={"fields": {"checksum": checksum, "pdf_id": str(record.id)}},
        )
    return record


async def update_document(
    db: AsyncIOMotorDatabase, document_id: str, request: PersistUpdateRequest
) -> PersistRecord:
    record = await repo_update_document(db, document_id, request)
    logger.info(
        "document updated",
        extra={
            "fields": {
                "pdf_id": document_id,
                "status": record.status,
            }
        },
    )
    return record


async def list_documents(
    db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
) -> list[PersistRecord]:
    return await repo_list_documents(db, skip=skip, limit=limit)


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    deleted = await repo_delete_document(db, document_id)
    if deleted:
        logger.info(
            "document deleted",
            extra={"fields": {"pdf_id": document_id}},
        )
    return deleted
