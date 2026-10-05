from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pdf_persistence.api import router as documents_router
from pdf_persistence.db import get_db
from pdf_persistence.models import PersistRecord, PersistCreateRequest

@pytest.fixture
def app() -> FastAPI:
    _app = FastAPI()
    _app.include_router(documents_router)
    return _app

@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()

@pytest.fixture
def test_app(app: FastAPI, mock_db: AsyncMock) -> FastAPI:
    app.dependency_overrides[get_db] = lambda: mock_db
    return app

@pytest.mark.asyncio
@patch("pdf_persistence.api.create_document")
async def test_upload_document(
    mock_process: AsyncMock,
    test_app: FastAPI,
) -> None:
    mock_doc = PersistRecord(
        id="fake_doc_id",
        checksum="123",
        original_format="pdf",
        title="Test",
        status="pending",
        created_at="2024-01-01T00:00:00Z"
    )
    mock_process.return_value = mock_doc
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/documents",
            json={"title": "Test", "checksum": "123", "status": "pending", "original_format": "pdf"}
        )
        
    assert response.status_code == 201
    assert response.json()["id"] == "fake_doc_id"
    mock_process.assert_awaited_once()

@pytest.mark.asyncio
@patch("pdf_persistence.api.get_document")
async def test_get_document(
    mock_get: AsyncMock,
    test_app: FastAPI,
) -> None:
    mock_doc = PersistRecord(
        id="fake_doc_id",
        content="Markdown",
        checksum="123",
        original_format="markdown",
        title="Test",
        status="done",
        created_at="2024-01-01T00:00:00Z"
    )
    mock_get.return_value = mock_doc
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/documents/fake_doc_id")
        
    assert response.status_code == 200
    assert response.json()["id"] == "fake_doc_id"
    mock_get.assert_awaited_once()

@pytest.mark.asyncio
@patch("pdf_persistence.api.list_documents")
async def test_list_documents(
    mock_list: AsyncMock,
    test_app: FastAPI,
) -> None:
    mock_list.return_value = []
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/documents?skip=10&limit=5")
        
    assert response.status_code == 200
    assert response.json() == []
    mock_list.assert_awaited_once()

@pytest.mark.asyncio
@patch("pdf_persistence.api.delete_document")
async def test_delete_document_success(
    mock_delete: AsyncMock,
    test_app: FastAPI,
) -> None:
    mock_delete.return_value = True
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.delete("/documents/fake_doc_id")
        
    assert response.status_code == 204
    mock_delete.assert_awaited_once()
