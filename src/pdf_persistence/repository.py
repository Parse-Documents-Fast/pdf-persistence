import logging
import zlib
from datetime import UTC, datetime
from typing import Any

import pymongo.errors
import redis.exceptions
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from dev.config import settings
from pdf_persistence.cache import get_redis
from pdf_persistence.models import (
    PersistCreateRequest,
    PersistRecord,
    PersistUpdateRequest,
)
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DocumentTooLargeException,
    DuplicateDocumentException,
)

logger = logging.getLogger(__name__)

BSON_CONTENT_INLINE_LIMIT = 1024 * 1024  # 1 MiB

REDIS_CACHE_ERRORS = (
    redis.exceptions.RedisError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _pack_content(data: dict[str, Any]) -> dict[str, Any]:
    content = data.get("content")
    if isinstance(content, str):
        raw_bytes = content.encode("utf-8")
        if len(raw_bytes) > BSON_CONTENT_INLINE_LIMIT:
            packed = dict(data)
            packed["content"] = None
            packed["content_compressed"] = zlib.compress(raw_bytes, level=1)
            return packed
    return data


def _unpack_record(doc_dict: dict[str, Any]) -> PersistRecord:
    compressed = doc_dict.get("content_compressed")
    if compressed is not None:
        doc_dict = dict(doc_dict)
        doc_dict["content"] = zlib.decompress(compressed).decode("utf-8")
    return PersistRecord.model_validate(doc_dict)


async def create_document(
    db: AsyncIOMotorDatabase, doc: PersistCreateRequest
) -> PersistRecord:
    collection = db["documents"]
    doc_dict = _pack_content(doc.model_dump())
    doc_dict["created_at"] = datetime.now(UTC)
    doc_dict["error"] = doc_dict.get("error", None)

    try:
        result = await collection.insert_one(doc_dict)
        doc_dict["_id"] = result.inserted_id

        # Guardar en redis de forma best-effort
        try:
            redis_client = get_redis()
            cache_key = f"dedupe:checksum:{doc.checksum}"
            await redis_client.set(
                cache_key, str(result.inserted_id), ex=settings.REDIS_TTL
            )
        except REDIS_CACHE_ERRORS as err:
            logger.warning("Failed to cache checksum in Redis: %s", err)

        return _unpack_record(doc_dict)
    except pymongo.errors.DuplicateKeyError as e:
        raise DuplicateDocumentException(checksum=doc.checksum) from e
    except pymongo.errors.DocumentTooLarge as e:
        raise DocumentTooLargeException() from e


async def get_document_by_id(
    db: AsyncIOMotorDatabase, document_id: str
) -> PersistRecord:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)

    collection = db["documents"]
    doc_dict = await collection.find_one({"_id": ObjectId(document_id)})

    if not doc_dict:
        raise DocumentNotFoundException(document_id=document_id)

    return _unpack_record(doc_dict)


async def update_document(
    db: AsyncIOMotorDatabase, document_id: str, updates: PersistUpdateRequest
) -> PersistRecord:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)

    collection = db["documents"]
    raw_updates = updates.model_dump(exclude_unset=True)
    if not raw_updates:
        return await get_document_by_id(db, document_id)

    update_data = _pack_content(raw_updates)
    if "content" in raw_updates and "content_compressed" not in update_data:
        update_data["content_compressed"] = None

    try:
        result = await collection.find_one_and_update(
            {"_id": ObjectId(document_id)},
            {"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )
    except pymongo.errors.DocumentTooLarge as e:
        raise DocumentTooLargeException() from e

    if not result:
        raise DocumentNotFoundException(document_id=document_id)
    return _unpack_record(result)


async def get_document_by_checksum(
    db: AsyncIOMotorDatabase, checksum: str
) -> PersistRecord | None:
    cache_key = f"dedupe:checksum:{checksum}"

    try:
        redis_client = get_redis()
        cached_id = await redis_client.get(cache_key)
        if cached_id:
            try:
                return await get_document_by_id(db, cached_id)
            except DocumentNotFoundException:
                pass
    except REDIS_CACHE_ERRORS as err:
        logger.warning("Cache lookup failed for checksum %s: %s", checksum, err)

    collection = db["documents"]
    doc_dict = await collection.find_one({"checksum": checksum})

    if not doc_dict:
        return None

    doc_resp = _unpack_record(doc_dict)
    try:
        redis_client = get_redis()
        await redis_client.set(cache_key, str(doc_resp.id), ex=settings.REDIS_TTL)
    except REDIS_CACHE_ERRORS as err:
        logger.warning("Failed to update cache for checksum %s: %s", checksum, err)

    return doc_resp


async def list_documents(
    db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
) -> list[PersistRecord]:
    collection = db["documents"]
    cursor = collection.find().skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    return [_unpack_record(doc) for doc in documents]


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)

    collection = db["documents"]
    doc = await collection.find_one({"_id": ObjectId(document_id)})
    if doc and "checksum" in doc:
        try:
            redis_client = get_redis()
            cache_key = f"dedupe:checksum:{doc['checksum']}"
            await redis_client.delete(cache_key)
        except REDIS_CACHE_ERRORS as err:
            logger.warning("Failed to evict cache key on delete: %s", err)

    result = await collection.delete_one({"_id": ObjectId(document_id)})
    return result.deleted_count > 0
