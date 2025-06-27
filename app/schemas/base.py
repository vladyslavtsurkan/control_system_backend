from uuid import UUID

from pydantic import BaseModel

__all__ = ["IdBase"]


class IdBase(BaseModel):
    id: UUID
