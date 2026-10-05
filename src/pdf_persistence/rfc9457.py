from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class ProblemDetails(BaseModel):
    type: str = Field(default="about:blank", description="URI reference identifying problem type")
    title: str = Field(..., description="Short, human-readable summary of problem type")
    status: int = Field(..., description="HTTP status code")
    detail: str | None = Field(default=None, description="Human-readable explanation specific to this occurrence")
    instance: str | None = Field(default=None, description="URI reference identifying specific occurrence")

    model_config = ConfigDict(extra="allow")


def problem_details_response(
    status: int,
    title: str,
    detail: str | None = None,
    type_: str = "about:blank",
    instance: str | None = None,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> JSONResponse:
    """Generate a standard RFC 9457 JSONResponse with application/problem+json media type."""
    problem = ProblemDetails(
        type=type_,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        **kwargs,
    )
    response_headers = {"Content-Type": "application/problem+json"}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(exclude_none=True),
        headers=response_headers,
    )


class DomainException(Exception):
    """Base domain exception with RFC 9457 attributes."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str | None = None,
        type_: str = "about:blank",
        instance: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(detail or title)
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_ = type_
        self.instance = instance
        self.extra = kwargs
    def to_problem_details(self) -> dict[str, Any]:
        return {
            "status": self.status_code,
            "title": self.title,
            "detail": self.detail,
            "type_": self.type_,
            "instance": self.instance,
            **self.extra,
        }


class DocumentNotFoundException(DomainException):
    def __init__(self, document_id: str, instance: str | None = None) -> None:
        super().__init__(
            status_code=404,
            title="Document Not Found",
            detail=f"Document with id '{document_id}' was not found.",
            instance=instance,
        )


class DuplicateDocumentException(DomainException):
    def __init__(self, checksum: str, instance: str | None = None) -> None:
        super().__init__(
            status_code=409,
            title="Conflict - Duplicate Document",
            detail=f"Document with checksum '{checksum}' already exists.",
            instance=instance,
        )
