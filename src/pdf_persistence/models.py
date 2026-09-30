from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field


def _convert_id_to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


PyObjectId = Annotated[str, BeforeValidator(_convert_id_to_str)]


class DocumentBase(BaseModel):
    content: str = Field(..., min_length=1, description="Markdown canonical content")
    checksum: str = Field(..., min_length=1, description="Document checksum (SHA-256)")
    original_format: str = Field(default="pdf", description="Original format before Markdown conversion")
    title: str | None = Field(default=None, description="Document title or filename")


class DocumentCreate(DocumentBase):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of document creation (UTC)",
    )


class DocumentResponse(DocumentBase):
    id: PyObjectId = Field(
        ...,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
        description="Unique document identifier",
    )
    created_at: datetime = Field(..., description="Timestamp of document creation (UTC)")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
