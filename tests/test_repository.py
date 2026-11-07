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


@pytest.mark.asyncio
async def test_db_lifespan_uses_tz_aware():
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from dev.config import settings
    from pdf_persistence.db import lifespan

    @asynccontextmanager
    async def dummy_cache_lifespan(_app):
        yield

    app = FastAPI()
    with (
        patch("pdf_persistence.db.AsyncIOMotorClient") as mock_motor_cls,
        patch("pdf_persistence.db.setup_indexes", new_callable=AsyncMock),
        patch("pdf_persistence.cache.lifespan", dummy_cache_lifespan),
    ):
        async with lifespan(app):
            mock_motor_cls.assert_called_once_with(settings.MONGO_URL, tz_aware=True)


@pytest.mark.asyncio
@patch("pdf_persistence.repository.get_redis")
async def test_create_and_read_19mb_markdown_content(mock_get_redis):
    import bson

    from pdf_persistence.models import PersistUpdateRequest
    from pdf_persistence.repository import get_document_by_id, update_document

    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    stored_doc = {}

    async def fake_insert_one(doc_dict):
        # Verify the BSON encoded document is well below MongoDB's 16 MiB limit
        raw_bson = bson.encode(doc_dict)
        assert len(raw_bson) < 16 * 1024 * 1024
        stored_doc.update(doc_dict)
        stored_doc["_id"] = bson.ObjectId("665f1a2b3c4d5e6f7a8b9c0d")
        return AsyncMock(inserted_id=stored_doc["_id"])

    async def fake_find_one(_query):
        return dict(stored_doc)

    async def fake_find_one_and_update(_query, update_op, **_kwargs):
        stored_doc.update(update_op["$set"])
        raw_bson = bson.encode(stored_doc)
        assert len(raw_bson) < 16 * 1024 * 1024
        return dict(stored_doc)

    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.insert_one.side_effect = fake_insert_one
    mock_collection.find_one.side_effect = fake_find_one
    mock_collection.find_one_and_update.side_effect = fake_find_one_and_update

    content_19mb = "# Titulo\n" + ("Texto de prueba en Markdown.\n" * 700_000)
    assert len(content_19mb.encode("utf-8")) > 19 * 1024 * 1024

    req = PersistCreateRequest(
        title="Large 19MB MD",
        checksum="hash19mb",
        status="done",
        original_format="markdown",
        content=content_19mb,
    )

    created = await create_document(mock_db, req)
    assert created.content == content_19mb
    assert stored_doc["content"] is None
    assert "content_compressed" in stored_doc

    fetched = await get_document_by_id(mock_db, "665f1a2b3c4d5e6f7a8b9c0d")
    assert fetched.content == content_19mb

    updated = await update_document(
        mock_db,
        "665f1a2b3c4d5e6f7a8b9c0d",
        PersistUpdateRequest(status="done", content=content_19mb),
    )
    assert updated.content == content_19mb


@pytest.mark.asyncio
async def test_document_too_large_exception_handling():
    from pdf_persistence.models import PersistUpdateRequest
    from pdf_persistence.repository import update_document
    from pdf_persistence.rfc9457 import DocumentTooLargeException

    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.insert_one.side_effect = pymongo.errors.DocumentTooLarge(
        "BSON document too large"
    )
    mock_collection.find_one_and_update.side_effect = pymongo.errors.DocumentTooLarge(
        "BSON document too large"
    )

    req = PersistCreateRequest(
        title="TooLarge",
        checksum="hash_huge",
        status="done",
        original_format="markdown",
    )
    with pytest.raises(DocumentTooLargeException) as exc_create:
        await create_document(mock_db, req)
    assert exc_create.value.status_code == 413

    with pytest.raises(DocumentTooLargeException) as exc_update:
        await update_document(
            mock_db,
            "665f1a2b3c4d5e6f7a8b9c0d",
            PersistUpdateRequest(status="done", content="x"),
        )
    assert exc_update.value.status_code == 413
