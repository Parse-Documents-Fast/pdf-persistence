from unittest.mock import AsyncMock

import pymongo.errors
import pytest
from bson import ObjectId

from pdf_persistence.models import DocumentCreate
from pdf_persistence.repository import (
    create_document,
    get_document_by_checksum,
    get_document_by_id,
)
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DuplicateDocumentException,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_document_success(mock_db: AsyncMock) -> None:
    doc = DocumentCreate(
        content="Hello world",
        checksum="123456",
        title="Test",
    )
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_insert_result = AsyncMock()
    mock_insert_result.inserted_id = ObjectId()
    mock_collection.insert_one.return_value = mock_insert_result
    
    doc_id = await create_document(mock_db, doc)
    
    assert doc_id == str(mock_insert_result.inserted_id)
    mock_collection.insert_one.assert_awaited_once_with(doc.model_dump())


@pytest.mark.asyncio
async def test_create_document_duplicate(mock_db: AsyncMock) -> None:
    doc = DocumentCreate(
        content="Hello world",
        checksum="dup_checksum",
    )
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_collection.insert_one.side_effect = pymongo.errors.DuplicateKeyError("Duplicate")
    
    with pytest.raises(DuplicateDocumentException) as exc_info:
        await create_document(mock_db, doc)
        
    assert "dup_checksum" in exc_info.value.detail  # type: ignore[operator]


@pytest.mark.asyncio
async def test_get_document_by_id_success(mock_db: AsyncMock) -> None:
    doc_id_str = str(ObjectId())
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_doc = {
        "_id": ObjectId(doc_id_str),
        "content": "Valid Content",
        "checksum": "checksum123",
        "original_format": "markdown",
        "title": "Document",
        "created_at": "2024-01-01T00:00:00Z",
    }
    mock_collection.find_one.return_value = mock_doc
    
    result = await get_document_by_id(mock_db, doc_id_str)
    
    assert result.id == doc_id_str
    assert result.content == "Valid Content"
    mock_collection.find_one.assert_awaited_once_with({"_id": ObjectId(doc_id_str)})


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(mock_db: AsyncMock) -> None:
    doc_id_str = str(ObjectId())
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find_one.return_value = None
    
    with pytest.raises(DocumentNotFoundException) as exc_info:
        await get_document_by_id(mock_db, doc_id_str)
        
    assert doc_id_str in exc_info.value.detail  # type: ignore[operator]


@pytest.mark.asyncio
async def test_get_document_by_id_invalid_id(mock_db: AsyncMock) -> None:
    with pytest.raises(DocumentNotFoundException) as exc_info:
        await get_document_by_id(mock_db, "invalid_object_id")
        
    assert "invalid_object_id" in exc_info.value.detail  # type: ignore[operator]


@pytest.mark.asyncio
async def test_get_document_by_checksum_success(mock_db: AsyncMock) -> None:
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_doc = {
        "_id": ObjectId(),
        "content": "Valid Content",
        "checksum": "checksum123",
        "original_format": "markdown",
        "title": "Document",
        "created_at": "2024-01-01T00:00:00Z",
    }
    mock_collection.find_one.return_value = mock_doc
    
    result = await get_document_by_checksum(mock_db, "checksum123")
    
    assert result is not None
    assert result.checksum == "checksum123"
    assert result.content == "Valid Content"
    mock_collection.find_one.assert_awaited_once_with({"checksum": "checksum123"})


@pytest.mark.asyncio
async def test_get_document_by_checksum_not_found(mock_db: AsyncMock) -> None:
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find_one.return_value = None
    
    result = await get_document_by_checksum(mock_db, "missing_checksum")
    
    assert result is None
    mock_collection.find_one.assert_awaited_once_with({"checksum": "missing_checksum"})
