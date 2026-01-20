from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

__all__ = ["IdBase", "TimestampBase"]


class IdBase(BaseModel):
    id: UUID


class TimestampBase(BaseModel):
    created_at: datetime
    updated_at: datetime
