from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row, select

from app.models import Sensor, Reading, AlertRule, Alert
from app.models.opc_server import OpcServer
from app.repositories.base import BaseRepository

__all__ = ["SensorRepository", "ReadingRepository", "AlertRuleRepository", "AlertRepository"]


class SensorRepository(BaseRepository[Sensor]):
    model = Sensor


class ReadingRepository(BaseRepository[Reading]):
    model = Reading


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule

    async def get_active_with_org(self) -> Sequence[Row[tuple[AlertRule, UUID]]]:
        """Return all active alert rules joined with their organization_id.

        Joins ``AlertRule → Sensor → OpcServer`` in a single query so callers
        receive ``(AlertRule, organization_id)`` pairs without extra round-trips.
        """
        stmt = (
            select(AlertRule, OpcServer.organization_id)
            .join(Sensor, AlertRule.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .where(AlertRule.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.all()


class AlertRepository(BaseRepository[Alert]):
    model = Alert
