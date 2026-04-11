from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, func, and_, desc

from app.core.constants import PAGINATION_PER_PAGE
from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository

__all__ = ["AuditLogRepository"]


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def get_for_org(
        self,
        organization_id: UUID,
        resource_type: AuditResourceTypeEnum | None = None,
        action: AuditActionEnum | None = None,
        actor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> tuple[Sequence[AuditLog], int]:
        """Return paginated audit logs for an organization, newest first."""
        filters: dict = {"organization_id": organization_id}
        if resource_type is not None:
            filters["resource_type"] = resource_type
        if action is not None:
            filters["action"] = action
        if actor_id is not None:
            filters["actor_id"] = actor_id

        stmt = (
            select(AuditLog, func.count().over().label("total_count"))
            .where(and_(*self.get_where_clauses(filters)))
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        if rows:
            items = [row[0] for row in rows]
            total = rows[0][1]
        else:
            items = []
            total = 0

        return items, total
