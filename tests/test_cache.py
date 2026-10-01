import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from datetime import datetime, UTC

from pdf_persistence.models import DocumentCreate, DocumentResponse
from pdf_persistence.repository import (
    create_document,
    get_document_by_checksum,
    delete_document,
)

@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()

@pytest.fixture
def mock_redis() -> AsyncMock:
    redis_client = AsyncMock()
    redis_client.set = AsyncMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.delete = AsyncMock()
    return redis_client

@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_cache_hit_find_by_checksum(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    
    # Simular que hay un hit en cache devolviendo un ID
    cached_id = str(ObjectId())
    mock_redis.get.return_value = cached_id
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    result = await get_document_by_checksum(mock_db, "some_checksum")
    
    assert result is not None
    assert result.id == cached_id
    assert result.content == "cached"
    
    # Verificar que NO se llamo a mongo
    mock_collection.find_one.assert_not_called()
    mock_redis.get.assert_called_once_with("dedupe:checksum:some_checksum")

@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_cache_miss_find_by_checksum(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    
    # Simular que NO hay hit en cache
    mock_redis.get.return_value = None
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    mock_doc = {
        "_id": ObjectId(),
        "content": "Valid Content",
        "checksum": "some_checksum",
        "original_format": "markdown",
        "title": "Document",
        "created_at": datetime.now(UTC),
    }
    mock_collection.find_one.return_value = mock_doc
    
    result = await get_document_by_checksum(mock_db, "some_checksum")
    
    assert result is not None
    assert result.id == str(mock_doc["_id"])
    
    # Verificar que SI se llamo a mongo
    mock_collection.find_one.assert_called_once_with({"checksum": "some_checksum"})
    
    # Verificar que SI se llamo a redis set con TTL
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "dedupe:checksum:some_checksum"
    assert args[1] == str(mock_doc["_id"])
    assert "ex" in kwargs

@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_cache_invalidation_delete(mock_get_redis: AsyncMock, mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    mock_get_redis.return_value = mock_redis
    
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    
    # Simular que el documento existe
    doc_id = str(ObjectId())
    mock_collection.find_one.return_value = {"_id": ObjectId(doc_id), "checksum": "checksum_to_del"}
    
    mock_delete_result = AsyncMock()
    mock_delete_result.deleted_count = 1
    mock_collection.delete_one.return_value = mock_delete_result
    
    result = await delete_document(mock_db, doc_id)
    
    assert result is True
    mock_redis.delete.assert_called_once_with("dedupe:checksum:checksum_to_del")
