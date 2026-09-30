import json

from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DuplicateDocumentException,
    ProblemDetails,
    problem_details_response,
)


def test_problem_details_model() -> None:
    problem = ProblemDetails(
        status=404,
        title="Document Not Found",
        detail="The requested document does not exist.",
        instance="/documents/123",
        custom_code="DOC_NOT_FOUND",
    )
    assert problem.status == 404
    assert problem.title == "Document Not Found"
    assert problem.detail == "The requested document does not exist."
    assert problem.type == "about:blank"
    assert problem.instance == "/documents/123"
    dumped = problem.model_dump()
    assert dumped["custom_code"] == "DOC_NOT_FOUND"


def test_problem_details_response() -> None:
    response = problem_details_response(
        status=404,
        title="Document Not Found",
        detail="Document 60d5ecb54 not found.",
        instance="/documents/60d5ecb54",
    )
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"

    body = json.loads(response.body.decode("utf-8"))
    assert body["status"] == 404
    assert body["title"] == "Document Not Found"
    assert body["detail"] == "Document 60d5ecb54 not found."
    assert body["type"] == "about:blank"
    assert body["instance"] == "/documents/60d5ecb54"


def test_domain_exceptions() -> None:
    exc_404 = DocumentNotFoundException(document_id="12345", instance="/documents/12345")
    assert exc_404.status_code == 404
    assert exc_404.title == "Document Not Found"
    assert "12345" in (exc_404.detail or "")
    assert exc_404.instance == "/documents/12345"

    exc_409 = DuplicateDocumentException(checksum="sha256abc")
    assert exc_409.status_code == 409
    assert exc_409.title == "Conflict - Duplicate Document"
    assert "sha256abc" in (exc_409.detail or "")
