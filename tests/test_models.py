from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pdf_persistence.models import DocumentCreate, DocumentResponse


def test_document_create_valid() -> None:
    doc = DocumentCreate(
        content="# Title\n\nContent here.",
        checksum="a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
        original_format="pdf",
        title="Test Document",
    )
    assert doc.content == "# Title\n\nContent here."
    assert doc.checksum == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
    assert doc.original_format == "pdf"
    assert doc.title == "Test Document"
    assert isinstance(doc.created_at, datetime)


def test_document_create_validation_empty_content() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(
            content="",
            checksum="a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
        )


def test_document_create_validation_missing_checksum() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(content="Valid content")  # type: ignore[call-arg]


def test_document_response_from_dict_with_id() -> None:
    now = datetime.now(UTC)
    data = {
        "id": "60d5ecb54fa92f001c8e1234",
        "content": "# Valid Content",
        "checksum": "checksum123",
        "original_format": "markdown",
        "title": "Document",
        "created_at": now,
    }
    res = DocumentResponse.model_validate(data)
    assert res.id == "60d5ecb54fa92f001c8e1234"
    assert res.content == "# Valid Content"
    assert res.checksum == "checksum123"
    assert res.original_format == "markdown"
    assert res.title == "Document"
    assert res.created_at == now

    dumped = res.model_dump()
    assert dumped["id"] == "60d5ecb54fa92f001c8e1234"


def test_document_response_from_mongo_id_alias() -> None:
    now = datetime.now(UTC)
    mongo_doc = {
        "_id": "60d5ecb54fa92f001c8e1234",
        "content": "# Mongo Doc",
        "checksum": "abcde123",
        "created_at": now,
    }
    res = DocumentResponse.model_validate(mongo_doc)
    assert res.id == "60d5ecb54fa92f001c8e1234"
    assert res.original_format == "pdf"
    assert res.title is None
