from unittest.mock import AsyncMock, patch

import pymongo.errors
import pytest
from bson import ObjectId

from pdf_persistence.models import DocumentCreate
from pdf_persistence.repository import (
    create_document,
    delete_document,
    get_document_by_checksum,
    get_document_by_id,
    list_documents,
)
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DuplicateDocumentException,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    return db


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis_client = AsyncMock()
    # Para el método set de redis
    redis_client.set = AsyncMock()
    # Para get, return None for cache miss by default
    redis_client.get = AsyncMock(return_value=None)
    # Para delete
    redis_client.delete = AsyncMock()
    return redis_client


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_create_document_success(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
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
@patch("pdf_persistence.repository.get_redis")
async def test_create_document_duplicate(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
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
@patch("pdf_persistence.repository.get_redis")
async def test_get_document_by_checksum_success(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
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
@patch("pdf_persistence.repository.get_redis")
async def test_get_document_by_checksum_not_found(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find_one.return_value = None
    
    result = await get_document_by_checksum(mock_db, "missing_checksum")
    
    assert result is None
    mock_collection.find_one.assert_awaited_once_with({"checksum": "missing_checksum"})


@pytest.mark.asyncio
async def test_list_documents(mock_db: AsyncMock) -> None:
    from unittest.mock import MagicMock
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_cursor = MagicMock()
    # Motor's find() is synchronous and returns a cursor
    mock_collection.find = MagicMock(return_value=mock_cursor)
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock()
    
    mock_doc = {
        "_id": ObjectId(),
        "content": "Valid Content",
        "checksum": "checksum123",
        "original_format": "markdown",
        "title": "Document",
        "created_at": "2024-01-01T00:00:00Z",
    }
    mock_cursor.to_list.return_value = [mock_doc, mock_doc]
    
    result = await list_documents(mock_db, skip=10, limit=2)
    
    assert len(result) == 2
    assert result[0].checksum == "checksum123"
    mock_collection.find.assert_called_once_with()
    mock_cursor.skip.assert_called_once_with(10)
    mock_cursor.limit.assert_called_once_with(2)
    mock_cursor.to_list.assert_awaited_once_with(length=2)


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_delete_document_success(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    doc_id_str = str(ObjectId())
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_delete_result = AsyncMock()
    mock_delete_result.deleted_count = 1
    mock_collection.delete_one.return_value = mock_delete_result
    
    result = await delete_document(mock_db, doc_id_str)
    
    assert result is True
    mock_collection.delete_one.assert_awaited_once_with({"_id": ObjectId(doc_id_str)})


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_delete_document_not_found(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    doc_id_str = str(ObjectId())
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_delete_result = AsyncMock()
    mock_delete_result.deleted_count = 0
    mock_collection.delete_one.return_value = mock_delete_result
    
    result = await delete_document(mock_db, doc_id_str)
    
    assert result is False
    mock_collection.delete_one.assert_awaited_once_with({"_id": ObjectId(doc_id_str)})


@pytest.mark.asyncio
async def test_delete_document_invalid_id(mock_db: AsyncMock) -> None:
    with pytest.raises(DocumentNotFoundException) as exc_info:
        await delete_document(mock_db, "invalid_id")
        
    assert "invalid_id" in exc_info.value.detail  # type: ignore[operator]
