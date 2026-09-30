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
