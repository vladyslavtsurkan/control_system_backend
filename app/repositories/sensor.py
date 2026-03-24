from datetime import datetime, timedelta
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row, select, and_, func, desc, asc, cast
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import joinedload

from app.models import Sensor, Reading, AlertRule, Alert, Organization
from app.models.opc_server import OpcServer
from app.repositories.base import BaseRepository

__all__ = ["SensorRepository", "ReadingRepository", "AlertRuleRepository", "AlertRepository"]


class SensorRepository(BaseRepository[Sensor]):
    model = Sensor

    async def get_active_for_tenant(self, sensor_id: UUID, tenant_id: UUID) -> Sensor | None:
        stmt = (
            select(Sensor)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Sensor.id == sensor_id,
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_multi_for_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 10,
        opc_server_id: UUID | None = None,
    ) -> tuple[Sequence[Sensor], int]:
        stmt = (
            select(Sensor, func.count().over().label("total_count"))
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
            .offset(offset)
            .limit(limit)
        )
        if opc_server_id:
            stmt = stmt.where(OpcServer.id == opc_server_id)

        rows = (await self._session.execute(stmt)).all()
        if not rows:
            return [], 0
        return [row[0] for row in rows], rows[0][1]

    async def get_active_sensor_org_pairs(self) -> Sequence[Row[tuple[UUID, UUID]]]:
        """Return active ``(sensor_id, organization_id)`` pairs.

        Used by the worker cache so telemetry WS routing does not depend on
        alert-rule presence.
        """
        stmt = (
            select(Sensor.id, OpcServer.organization_id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Sensor.is_deleted.is_(False),
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.all()

    async def get_orgs_by_ids(self, sensor_ids: set[UUID]) -> dict[UUID, UUID]:
        """Return mapping of sensor_id to organization_id for given sensor_ids."""
        if not sensor_ids:
            return {}

        stmt = (
            select(Sensor.id, OpcServer.organization_id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .where(Sensor.id.in_(sensor_ids))
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}


class ReadingRepository(BaseRepository[Reading]):
    model = Reading

    async def get_in_time_range(
        self,
        sensor_id: UUID,
        start_time: datetime,
        end_time: datetime,
        bucket_interval: timedelta = timedelta(minutes=5),
    ) -> Sequence[Row[tuple[datetime, float]]]:
        time_bucket = func.time_bucket(cast(bucket_interval, INTERVAL), Reading.time)

        stmt = (
            select(
                time_bucket.label("time_bucket"),
                func.avg(Reading.val_num).label("avg_value"),
            )
            .where(
                Reading.sensor_id == sensor_id,
                Reading.time >= start_time,
                Reading.time <= end_time,
            )
            .group_by(time_bucket)
            .order_by(time_bucket.asc())
        )

        result = await self._session.execute(stmt)
        return result.all()

    async def get_recent_for_sensors(
        self,
        sensor_ids: Sequence[UUID],
        start_time: datetime,
        end_time: datetime,
    ) -> Sequence[Reading]:
        if not sensor_ids:
            return []

        stmt = (
            select(Reading)
            .where(
                Reading.sensor_id.in_(sensor_ids),
                Reading.time >= start_time,
                Reading.time <= end_time,
            )
            .order_by(Reading.sensor_id, Reading.time.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_bucketed_for_sensors(
        self,
        sensor_ids: Sequence[UUID],
        start_time: datetime,
        end_time: datetime,
        bucket_interval: timedelta = timedelta(minutes=5),
    ) -> Sequence[Row[tuple[UUID, datetime, float]]]:
        if not sensor_ids:
            return []

        time_bucket = func.time_bucket(cast(bucket_interval, INTERVAL), Reading.time)

        stmt = (
            select(
                Reading.sensor_id.label("sensor_id"),
                time_bucket.label("time_bucket"),
                func.avg(Reading.val_num).label("avg_value"),
            )
            .where(
                Reading.sensor_id.in_(sensor_ids),
                Reading.time >= start_time,
                Reading.time <= end_time,
            )
            .group_by(Reading.sensor_id, time_bucket)
            .order_by(Reading.sensor_id.asc(), time_bucket.asc())
        )

        result = await self._session.execute(stmt)
        return result.all()


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule

    async def get_for_tenant_by_id(self, alert_rule_id: UUID, tenant_id: UUID) -> AlertRule | None:
        stmt = (
            select(AlertRule)
            .join(Sensor, AlertRule.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                AlertRule.id == alert_rule_id,
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_multi_for_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 10,
        sensor_id: UUID | None = None,
        order_by: str | None = None,
    ) -> tuple[Sequence[AlertRule], int]:
        stmt = (
            select(AlertRule, func.count().over().label("total_count"))
            .join(Sensor, AlertRule.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
            .offset(offset)
            .limit(limit)
        )
        if sensor_id:
            stmt = stmt.where(Sensor.id == sensor_id)

        if order_by:
            if order_by.startswith("-"):
                stmt = stmt.order_by(desc(getattr(AlertRule, order_by[1:])).nulls_last())
            else:
                stmt = stmt.order_by(asc(getattr(AlertRule, order_by)))

        rows = (await self._session.execute(stmt)).all()
        if not rows:
            return [], 0
        return [row[0] for row in rows], rows[0][1]

    async def get_active_with_org(self) -> Sequence[Row[tuple[AlertRule, UUID]]]:
        """Return all active alert rules joined with their organization_id.

        Joins ``AlertRule → Sensor → OpcServer`` in a single query so callers
        receive ``(AlertRule, organization_id)`` pairs without extra round-trips.
        """
        stmt = (
            select(AlertRule, OpcServer.organization_id)
            .join(Sensor, AlertRule.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                AlertRule.is_active.is_(True),
                Sensor.is_deleted.is_(False),
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.all()


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    async def get_for_tenant_with_rule(self, alert_id: UUID, tenant_id: UUID) -> Alert | None:
        stmt = (
            select(Alert)
            .options(joinedload(Alert.rule))
            .join(Sensor, Alert.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Alert.id == alert_id,
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_multi_for_tenant_with_rule(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 10,
        sensor_id: UUID | None = None,
        order_by: str | None = None,
    ) -> tuple[Sequence[Alert], int]:
        stmt = (
            select(Alert, func.count().over().label("total_count"))
            .options(joinedload(Alert.rule))
            .join(Sensor, Alert.sensor_id == Sensor.id)
            .join(OpcServer, Sensor.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                Sensor.is_deleted.is_(False),
                OpcServer.organization_id == tenant_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
            .offset(offset)
            .limit(limit)
        )
        if sensor_id:
            stmt = stmt.where(Sensor.id == sensor_id)

        if order_by:
            if order_by.startswith("-"):
                stmt = stmt.order_by(desc(getattr(Alert, order_by[1:])).nulls_last())
            else:
                stmt = stmt.order_by(asc(getattr(Alert, order_by)))

        rows = (await self._session.execute(stmt)).all()
        if not rows:
            return [], 0
        return [row[0] for row in rows], rows[0][1]

    async def get_with_rule(self, filters: dict[str, Any], order_by: str | None = None) -> Alert | None:
        statement = select(Alert).options(joinedload(Alert.rule)).where(and_(*self.get_where_clauses(filters)))
        if order_by:
            if order_by.startswith("-"):
                statement = statement.order_by(desc(getattr(Alert, order_by[1:])).nulls_last())
            else:
                statement = statement.order_by(asc(getattr(Alert, order_by)))

        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_multi_with_rule(
        self,
        offset: int = 0,
        limit: int = 10,
        order_by: str | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Alert], int]:
        statement = (
            select(Alert, func.count().over().label("total_count"))
            .options(joinedload(Alert.rule))
            .where(*self.get_where_clauses(filters))
            .offset(offset)
            .limit(limit)
        )
        if order_by:
            if order_by.startswith("-"):
                statement = statement.order_by(desc(getattr(Alert, order_by[1:])).nulls_last())
            else:
                statement = statement.order_by(asc(getattr(Alert, order_by)))

        result = await self._session.execute(statement)
        rows = result.all()

        if rows:
            alerts = [row[0] for row in rows]
            total_count = rows[0][1]
        else:
            alerts = []
            total_count = 0

        return alerts, total_count

    async def get_active_by_sensor_rule(self, sensor_id: UUID, rule_id: UUID) -> Alert | None:
        return await self.get(
            filters={"sensor_id": sensor_id, "rule_id": rule_id, "resolved_at": None},
            order_by="-id",
        )

    async def update_active_by_id(self, alert_id: UUID, updates: dict[str, Any]) -> bool:
        affected = await self.update_many(
            filters={"id": alert_id, "resolved_at": None},
            updates=updates,
        )
        return affected > 0

    async def resolve_by_id_if_active(self, alert_id: UUID, resolved_at: datetime) -> bool:
        affected = await self.update_many(
            filters={"id": alert_id, "resolved_at": None},
            updates={"resolved_at": resolved_at},
        )
        return affected > 0

    async def resolve_active_by_sensor_rule(self, sensor_id: UUID, rule_id: UUID, resolved_at) -> int:
        return await self.update_many(
            filters={"sensor_id": sensor_id, "rule_id": rule_id, "resolved_at": None},
            updates={"resolved_at": resolved_at},
        )
