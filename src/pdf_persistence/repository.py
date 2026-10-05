from datetime import UTC, datetime
import pymongo.errors
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from dev.config import settings
from pdf_persistence.cache import get_redis

from pdf_persistence.models import PersistCreateRequest, PersistRecord, PersistUpdateRequest
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DuplicateDocumentException,
)

async def create_document(db: AsyncIOMotorDatabase, doc: PersistCreateRequest) -> PersistRecord:
    collection = db["documents"]
    doc_dict = doc.model_dump()
    doc_dict["created_at"] = datetime.now(UTC)
    doc_dict["error"] = doc_dict.get("error", None)
    
    try:
        result = await collection.insert_one(doc_dict)
        doc_dict["_id"] = result.inserted_id
        
        # Guardar en redis
        redis_client = get_redis()
        cache_key = f"dedupe:checksum:{doc.checksum}"
        await redis_client.set(cache_key, str(result.inserted_id), ex=settings.REDIS_TTL)
        
        return PersistRecord.model_validate(doc_dict)
    except pymongo.errors.DuplicateKeyError as e:
        raise DuplicateDocumentException(checksum=doc.checksum) from e

async def get_document_by_id(db: AsyncIOMotorDatabase, document_id: str) -> PersistRecord:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)
    
    collection = db["documents"]
    doc_dict = await collection.find_one({"_id": ObjectId(document_id)})
    
    if not doc_dict:
        raise DocumentNotFoundException(document_id=document_id)
        
    return PersistRecord.model_validate(doc_dict)

async def update_document(db: AsyncIOMotorDatabase, document_id: str, updates: PersistUpdateRequest) -> PersistRecord:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)
        
    collection = db["documents"]
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return await get_document_by_id(db, document_id)
        
    result = await collection.find_one_and_update(
        {"_id": ObjectId(document_id)},
        {"$set": update_data},
        return_document=pymongo.ReturnDocument.AFTER
    )
    if not result:
        raise DocumentNotFoundException(document_id=document_id)
    return PersistRecord.model_validate(result)

async def get_document_by_checksum(db: AsyncIOMotorDatabase, checksum: str) -> PersistRecord | None:
    redis_client = get_redis()
    cache_key = f"dedupe:checksum:{checksum}"
    
    cached_id = await redis_client.get(cache_key)
    if cached_id:
        try:
            return await get_document_by_id(db, cached_id)
        except DocumentNotFoundException:
            pass
            
    collection = db["documents"]
    doc_dict = await collection.find_one({"checksum": checksum})
    
    if not doc_dict:
        return None
        
    doc_resp = PersistRecord.model_validate(doc_dict)
    await redis_client.set(cache_key, str(doc_resp.id), ex=settings.REDIS_TTL)
    
    return doc_resp

async def list_documents(
    db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
) -> list[PersistRecord]:
    collection = db["documents"]
    cursor = collection.find().skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    return [PersistRecord.model_validate(doc) for doc in documents]

async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)
        
    collection = db["documents"]
    doc = await collection.find_one({"_id": ObjectId(document_id)})
    if doc and "checksum" in doc:
        redis_client = get_redis()
        cache_key = f"dedupe:checksum:{doc['checksum']}"
        await redis_client.delete(cache_key)
        
    result = await collection.delete_one({"_id": ObjectId(document_id)})
    return result.deleted_count > 0
