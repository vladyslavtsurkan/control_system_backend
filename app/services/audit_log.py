from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.infra.database import set_tenant_context
from app.schemas.audit_log import AuditLogResponse
from app.schemas.base import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.mixins import TenantValidationMixin

if TYPE_CHECKING:
    from app.uow.sql import SQLUnitOfWork

__all__ = ["AuditLogService"]


class AuditLogService(TenantValidationMixin):
    @staticmethod
    async def log(
        uow: SQLUnitOfWork,
        organization_id: UUID,
        actor: UserResponse,
        action: AuditActionEnum,
        resource_type: AuditResourceTypeEnum,
        resource_id: UUID | None = None,
        resource_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Insert an audit log entry within the current UoW transaction.

        Always sets the tenant context on the session so that the RLS
        WITH CHECK constraint on audit_logs is satisfied – this is a no-op
        when the session already has the correct tenant context.
        """
        await set_tenant_context(uow.session, organization_id)
        await uow.audit_log.create(
            {
                "organization_id": organization_id,
                "actor_id": actor.id,
                "actor_email": actor.email,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "extra_data": metadata,
            }
        )

    async def get_audit_logs(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        resource_type: AuditResourceTypeEnum | None = None,
        action: AuditActionEnum | None = None,
        actor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[AuditLogResponse]:
        """Return paginated audit log entries for a tenant. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            logs, count = await uow.audit_log.get_for_org(
                organization_id=tenant_id,
                resource_type=resource_type,
                action=action,
                actor_id=actor_id,
                offset=offset,
                limit=limit,
            )
            return PaginatedResponse(
                items=[AuditLogResponse.model_validate(log) for log in logs],
                count=count,
                per_page=limit,
            )
