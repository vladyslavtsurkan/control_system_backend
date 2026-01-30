from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingResponse, AlertResponse
from app.uow.sql import SQLUnitOfWork

__all__ = ["ReadingService", "AlertService"]


class ReadingService:
    @staticmethod
    async def get_readings(
        uow: SQLUnitOfWork,
        sensor_id: UUID,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[ReadingResponse]:
        """Get readings for a sensor (filtered by RLS)."""
        async with uow:
            readings, count = await uow.reading.get_multi(
                offset=offset,
                limit=limit,
                sensor_id=sensor_id,
                order_by="-time",
            )
            return PaginatedResponse(
                items=[ReadingResponse.model_validate(r) for r in readings],
                count=count,
                per_page=limit,
            )


class AlertService:
    @staticmethod
    async def get_alerts(
        uow: SQLUnitOfWork,
        sensor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[AlertResponse]:
        """Get alerts (filtered by RLS and optionally by sensor)."""
        async with uow:
            filters = {}
            if sensor_id:
                filters["sensor_id"] = sensor_id

            alerts, count = await uow.alert.get_multi(
                offset=offset,
                limit=limit,
                order_by="-created_at",
                **filters,
            )
            return PaginatedResponse(
                items=[AlertResponse.model_validate(a) for a in alerts],
                count=count,
                per_page=limit,
            )
