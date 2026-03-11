from typing import Literal
from uuid import UUID

from pydantic import BaseModel

__all__ = ["WsBroadcastEvent", "WsTicketResponse"]


class WsBroadcastEvent(BaseModel):
    type: Literal["telemetry", "alert"]
    organization_id: UUID
    sensor_id: UUID
    data: dict


class WsTicketResponse(BaseModel):
    ticket: str
