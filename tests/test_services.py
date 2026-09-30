import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from pdf_persistence.models import DocumentResponse
from pdf_persistence.rfc9457 import DuplicateDocumentException
from pdf_persistence.services import get_document, process_and_save_pdf


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
@patch("pdf_persistence.services.get_document_by_checksum")
@patch("pdf_persistence.services.create_document")
@patch("pdf_persistence.services.pymupdf4llm")
@patch("pdf_persistence.services.fitz")
async def test_process_and_save_pdf_success(
    mock_fitz: MagicMock,
    mock_pymupdf: MagicMock,
    mock_create_doc: AsyncMock,
    mock_get_by_checksum: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    # Arrange
    file_bytes = b"dummy pdf content"
    title = "Test PDF"
    expected_checksum = hashlib.sha256(file_bytes).hexdigest()
    
    mock_get_by_checksum.return_value = None  # No duplicate found
    
    mock_doc_instance = MagicMock()
    mock_fitz.Document.return_value = mock_doc_instance
    mock_pymupdf.to_markdown.return_value = "## Markdown content"
    
    expected_id = str(ObjectId())
    mock_create_doc.return_value = expected_id

    # Act
    doc_id = await process_and_save_pdf(mock_db, file_bytes, title)

    # Assert
    assert doc_id == expected_id
    mock_get_by_checksum.assert_awaited_once_with(mock_db, expected_checksum)
    mock_fitz.Document.assert_called_once_with(stream=file_bytes, filetype="pdf")
    mock_pymupdf.to_markdown.assert_called_once_with(mock_doc_instance)
    
    # Assert payload was correct
    mock_create_doc.assert_awaited_once()
    args, _ = mock_create_doc.call_args
    passed_db, passed_payload = args
    assert passed_db is mock_db
    assert passed_payload.content == "## Markdown content"
    assert passed_payload.checksum == expected_checksum
    assert passed_payload.title == title


@pytest.mark.asyncio
@patch("pdf_persistence.services.get_document_by_checksum")
async def test_process_and_save_pdf_duplicate(
    mock_get_by_checksum: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    # Arrange
    file_bytes = b"dummy duplicate content"
    expected_checksum = hashlib.sha256(file_bytes).hexdigest()
    
    mock_existing_doc = MagicMock(spec=DocumentResponse)
    mock_get_by_checksum.return_value = mock_existing_doc

    # Act & Assert
    with pytest.raises(DuplicateDocumentException) as exc_info:
        await process_and_save_pdf(mock_db, file_bytes, "Duplicate Title")
        
    assert expected_checksum in exc_info.value.detail  # type: ignore[operator]


@pytest.mark.asyncio
@patch("pdf_persistence.services.get_document_by_id")
async def test_get_document(mock_get_by_id: AsyncMock, mock_db: AsyncMock) -> None:
    # Arrange
    doc_id = str(ObjectId())
    mock_response = MagicMock(spec=DocumentResponse)
    mock_get_by_id.return_value = mock_response

    # Act
    result = await get_document(mock_db, doc_id)

    # Assert
    assert result is mock_response
    mock_get_by_id.assert_awaited_once_with(mock_db, doc_id)
