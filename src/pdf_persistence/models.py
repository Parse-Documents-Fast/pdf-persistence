from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)


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

    @field_validator("created_at", mode="after")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        utc_dt = (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )
        return utc_dt.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
