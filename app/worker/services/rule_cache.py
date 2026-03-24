from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from app.enums import AlertConditionEnum, AlertSeverityEnum
from app.uow.sql import SQLUnitOfWork

__all__ = ["AlertRuleCached", "RuleCacheService", "rule_cache_service"]


@dataclass(frozen=True, slots=True)
class AlertRuleCached:
    id: UUID
    sensor_id: UUID
    condition: AlertConditionEnum
    threshold: dict
    duration_seconds: int
    severity: AlertSeverityEnum
    name: str


class RuleCacheService:
    def __init__(self) -> None:
        self._rules: dict[UUID, list[AlertRuleCached]] = {}
        self._sensor_org: dict[UUID, UUID] = {}

    async def load(self) -> None:
        rules_by_sensor: dict[UUID, list[AlertRuleCached]] = defaultdict(list)
        sensor_org: dict[UUID, UUID] = {}

        async with SQLUnitOfWork(bypass_rls=True) as uow:
            sensor_rows = await uow.sensor.get_active_sensor_org_pairs()
            for sensor_id, organization_id in sensor_rows:
                sensor_org[sensor_id] = organization_id

            rows = await uow.alert_rule.get_active_with_org()
            for rule_row, _ in rows:
                cached = AlertRuleCached(
                    id=rule_row.id,
                    sensor_id=rule_row.sensor_id,
                    condition=rule_row.condition,
                    threshold=rule_row.threshold,
                    duration_seconds=rule_row.duration_seconds,
                    severity=rule_row.severity,
                    name=rule_row.name,
                )
                rules_by_sensor[cached.sensor_id].append(cached)

        self._rules = dict(rules_by_sensor)
        self._sensor_org = sensor_org
        total = sum(len(v) for v in self._rules.values())
        logger.info(
            "Rule cache loaded: {total} rules across {rule_sensors} rule-sensors ({mapped_sensors} mapped sensors)",
            total=total,
            rule_sensors=len(self._rules),
            mapped_sensors=len(self._sensor_org),
        )

    def get_rules(self, sensor_id: UUID) -> list[AlertRuleCached]:
        return self._rules.get(sensor_id, [])

    def get_org_id(self, sensor_id: UUID) -> UUID | None:
        return self._sensor_org.get(sensor_id)

    def get_all_no_data_rules(self) -> list[AlertRuleCached]:
        return [
            rule for rules in self._rules.values() for rule in rules if rule.condition == AlertConditionEnum.no_data
        ]

    async def reload(self) -> None:
        logger.info("Rule cache reload triggered")
        await self.load()


rule_cache_service = RuleCacheService()
