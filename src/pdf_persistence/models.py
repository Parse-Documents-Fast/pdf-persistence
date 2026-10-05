from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field

def _convert_id_to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

PyObjectId = Annotated[str, BeforeValidator(_convert_id_to_str)]

class PersistCreateRequest(BaseModel):
    title: str | None = None
    original_format: str = "pdf"
    checksum: str = Field(..., min_length=1)
    status: str = "pending"
    content: str | None = None

class PersistUpdateRequest(BaseModel):
    status: str | None = None
    content: str | None = None
    error: str | None = None

class PersistRecord(BaseModel):
    id: PyObjectId = Field(
        ...,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    title: str | None = None
    original_format: str
    checksum: str
    status: str
    content: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
