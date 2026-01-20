from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.constants import PAGINATION_PER_PAGE

__all__ = ["IdBase", "TimestampBase", "PaginatedResponse", "ItemsResponse"]

M = TypeVar("M")


class IdBase(BaseModel):
    id: UUID


class CreatedAtBase(BaseModel):
    created_at: datetime


class UpdatedAtBase(BaseModel):
    updated_at: datetime


class TimestampBase(CreatedAtBase, UpdatedAtBase):
    pass


class PaginateBase(BaseModel):
    count: int = Field(description="Number of total items")
    per_page: int | None = Field(None, description="Number of items per page")
    total_pages: int | None = Field(None, description="Number of total pages")


class PaginatedResponse(PaginateBase, Generic[M]):
    items: list[M] = Field(default_factory=list, description="List of paginated items")

    @model_validator(mode="before")
    @classmethod
    def calculate_pagination(cls, values):
        count = values.get("count", 0)
        per_page = values.get("per_page", PAGINATION_PER_PAGE)
        if not per_page:
            per_page = len(values.get("items", [])) or 1
        values["total_pages"] = (count + per_page - 1) // per_page
        return values


class ItemsResponse(BaseModel, Generic[M]):
    items: list[M] = Field(default_factory=list, description="List of items")
