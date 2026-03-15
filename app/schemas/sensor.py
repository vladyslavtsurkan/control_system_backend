from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import IdBase, CreatedAtBase
from app.schemas.reading import ReadingResponse

__all__ = [
    "SensorBase",
    "SensorCreateRequest",
    "SensorUpdateRequest",
    "SensorResponse",
    "SensorWithReadingsResponse",
]


class SensorBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    node_id: str = Field(..., max_length=255)
    units: str | None = Field(None, max_length=50)


class SensorCreateRequest(SensorBase):
    opc_server_id: UUID


class SensorUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    node_id: str | None = Field(None, max_length=255)
    units: str | None = Field(None, max_length=50)


class SensorResponse(IdBase, CreatedAtBase):
    opc_server_id: UUID
    name: str
    description: str | None
    node_id: str
    units: str | None

    model_config = ConfigDict(from_attributes=True)


class SensorWithReadingsResponse(SensorResponse):
    readings: list[ReadingResponse] | None = None
