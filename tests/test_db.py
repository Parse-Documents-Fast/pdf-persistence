from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from pdf_persistence.db import db_manager, get_db, lifespan


@pytest.mark.asyncio
async def test_lifespan_initializes_and_closes_db() -> None:
    app = FastAPI()
    
    with patch("pdf_persistence.db.AsyncIOMotorClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_db_instance = AsyncMock()
        mock_collection = AsyncMock()
        
        # Setup mock behavior
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.__getitem__.return_value = mock_db_instance
        mock_db_instance.__getitem__.return_value = mock_collection
        
        async with lifespan(app):
            # Assert client was created
            mock_client_class.assert_called_once()
            assert db_manager.client is mock_client_instance
            assert db_manager.db is mock_db_instance
            
            # Assert setup_indexes was called (create_index on collection)
            mock_collection = mock_db_instance["documents"]
            mock_collection.create_index.assert_awaited_once()

        # Assert close was called
        mock_client_instance.close.assert_called_once()


def test_get_db_uninitialized() -> None:
    # Temporarily set to None
    old_db = db_manager.db
    db_manager.db = None
    try:
        with pytest.raises(RuntimeError, match="Database is not initialized"):
            get_db()
    finally:
        db_manager.db = old_db


def test_get_db_initialized() -> None:
    old_db = db_manager.db
    db_manager.db = "mock_db"  # type: ignore[assignment]
    try:
        assert get_db() == "mock_db"
    finally:
        db_manager.db = old_db
