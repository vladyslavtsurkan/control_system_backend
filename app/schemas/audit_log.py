from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum

__all__ = ["AuditLogResponse"]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    organization_id: UUID
    actor_id: UUID | None
    actor_email: str
    action: AuditActionEnum
    resource_type: AuditResourceTypeEnum
    resource_id: UUID | None = None
    resource_name: str | None = None
    extra_data: dict[str, Any] | None = None
