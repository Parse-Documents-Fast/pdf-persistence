import pymongo.errors
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from pdf_persistence.models import DocumentCreate, DocumentResponse
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DuplicateDocumentException,
)


async def create_document(db: AsyncIOMotorDatabase, doc: DocumentCreate) -> str:
    """
    Inserts a new document into the database.
    Raises DuplicateDocumentException if a document with the same checksum already exists.
    """
    collection = db["documents"]
    doc_dict = doc.model_dump()
    
    try:
        result = await collection.insert_one(doc_dict)
        return str(result.inserted_id)
    except pymongo.errors.DuplicateKeyError as e:
        raise DuplicateDocumentException(checksum=doc.checksum) from e


async def get_document_by_id(db: AsyncIOMotorDatabase, document_id: str) -> DocumentResponse:
    """
    Retrieves a document by its MongoDB ObjectId.
    Raises DocumentNotFoundException if it doesn't exist or if the ID is invalid.
    """
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)
    
    collection = db["documents"]
    doc_dict = await collection.find_one({"_id": ObjectId(document_id)})
    
    if not doc_dict:
        raise DocumentNotFoundException(document_id=document_id)
        
    return DocumentResponse.model_validate(doc_dict)


async def get_document_by_checksum(db: AsyncIOMotorDatabase, checksum: str) -> DocumentResponse | None:
    """
    Retrieves a document by its checksum to check for duplicates.
    Returns None if no document with the given checksum exists.
    """
    collection = db["documents"]
    doc_dict = await collection.find_one({"checksum": checksum})
    
    if not doc_dict:
        return None
        
    return DocumentResponse.model_validate(doc_dict)


async def list_documents(
    db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
) -> list[DocumentResponse]:
    """
    Retrieves a paginated list of documents.
    """
    collection = db["documents"]
    cursor = collection.find().skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    return [DocumentResponse.model_validate(doc) for doc in documents]


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    """
    Deletes a document by its ID.
    Returns True if the document was deleted, False if it was not found.
    Raises DocumentNotFoundException if the ID format is invalid.
    """
    if not ObjectId.is_valid(document_id):
        raise DocumentNotFoundException(document_id=document_id)
        
    collection = db["documents"]
    result = await collection.delete_one({"_id": ObjectId(document_id)})
    return result.deleted_count > 0
