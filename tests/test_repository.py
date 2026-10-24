from unittest.mock import AsyncMock, patch

import pydantic
import pymongo.errors
import pytest
import redis.exceptions

from dev.config import Settings
from pdf_persistence.models import PersistCreateRequest
from pdf_persistence.repository import (
    create_document,
    delete_document,
    get_document_by_checksum,
)
from pdf_persistence.rfc9457 import DuplicateDocumentException


def test_settings_requires_mongo_url(monkeypatch):
    monkeypatch.delenv("MONGO_URL", raising=False)
    with pytest.raises(pydantic.ValidationError):
        Settings(_env_file=None)


@pytest.mark.asyncio
async def test_create_document_duplicate_key_error():
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.insert_one.side_effect = pymongo.errors.DuplicateKeyError(
        "duplicate"
    )

    req = PersistCreateRequest(
        title="Doc", checksum="abc123hash", status="pending", original_format="pdf"
    )

    with pytest.raises(DuplicateDocumentException) as exc_info:
        await create_document(mock_db, req)

    assert "abc123hash" in exc_info.value.detail
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_create_document_best_effort_redis(mock_get_redis):
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.insert_one.return_value = AsyncMock(
        inserted_id="665f1a2b3c4d5e6f7a8b9c0d"
    )

    # Redis fails with error
    mock_redis = AsyncMock()
    mock_redis.set.side_effect = redis.exceptions.ConnectionError(
        "Redis connection timeout"
    )
    mock_get_redis.return_value = mock_redis

    req = PersistCreateRequest(
        title="Doc", checksum="abc123hash", status="pending", original_format="pdf"
    )

    # Must not raise error, must return PersistRecord successfully
    record = await create_document(mock_db, req)
    assert str(record.id) == "665f1a2b3c4d5e6f7a8b9c0d"
    assert record.checksum == "abc123hash"


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_get_document_by_checksum_fallback_on_redis_error(mock_get_redis):
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find_one.return_value = {
        "_id": "665f1a2b3c4d5e6f7a8b9c0d",
        "checksum": "abc123hash",
        "original_format": "pdf",
        "status": "pending",
        "title": "Doc",
        "created_at": "2026-10-05T14:30:00Z",
    }

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = redis.exceptions.ConnectionError("Redis error")
    mock_redis.set.side_effect = redis.exceptions.ConnectionError("Redis error")
    mock_get_redis.return_value = mock_redis

    # Fallback directly to MongoDB
    record = await get_document_by_checksum(mock_db, "abc123hash")
    assert record is not None
    assert str(record.id) == "665f1a2b3c4d5e6f7a8b9c0d"
    mock_collection.find_one.assert_awaited_once_with({"checksum": "abc123hash"})


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_delete_document_best_effort_redis(mock_get_redis):
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find_one.return_value = {
        "_id": "665f1a2b3c4d5e6f7a8b9c0d",
        "checksum": "abc123hash",
    }
    mock_collection.delete_one.return_value = AsyncMock(deleted_count=1)

    mock_redis = AsyncMock()
    mock_redis.delete.side_effect = redis.exceptions.ConnectionError("Redis error")
    mock_get_redis.return_value = mock_redis

    deleted = await delete_document(mock_db, "507f1f77bcf86cd799439011")
    assert deleted is True


@pytest.mark.asyncio
async def test_redis_cache_client_timeouts():
    from fastapi import FastAPI

    from pdf_persistence.cache import lifespan

    app = FastAPI()
    with patch("redis.asyncio.Redis") as mock_redis_cls:
        mock_instance = AsyncMock()
        mock_redis_cls.return_value = mock_instance
        async with lifespan(app):
            mock_redis_cls.assert_called_once_with(
                host="redis-cache",
                port=6379,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
                decode_responses=True,
            )


@pytest.mark.asyncio
async def test_setup_indexes_unauthorized_error(caplog):
    import logging

    from pdf_persistence.db import db_manager, setup_indexes

    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.create_index.side_effect = pymongo.errors.OperationFailure(
        "requires authentication", code=13
    )

    db_manager.db = mock_db
    with caplog.at_level(logging.ERROR), pytest.raises(pymongo.errors.OperationFailure):
        await setup_indexes()

    assert "Fallo de autenticacion al crear indices en MongoDB" in caplog.text
    assert "authSource" in caplog.text
