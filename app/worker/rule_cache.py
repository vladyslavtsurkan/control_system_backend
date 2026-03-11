from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from app.enums import AlertConditionEnum, AlertSeverityEnum
from app.uow.sql import SQLUnitOfWork

__all__ = ["AlertRuleCached", "RuleCache", "rule_cache"]


@dataclass(frozen=True, slots=True)
class AlertRuleCached:
    """Lightweight, immutable representation of an active alert rule."""

    id: UUID
    sensor_id: UUID
    condition: AlertConditionEnum
    threshold: dict
    severity: AlertSeverityEnum
    name: str


class RuleCache:
    """In-memory cache of active alert rules, keyed by sensor_id.

    Also maintains a ``sensor_id → organization_id`` mapping used by the
    WebSocket broadcast publisher so it can route events to the correct
    tenant without an extra DB round-trip per batch.
    """

    def __init__(self) -> None:
        self._rules: dict[UUID, list[AlertRuleCached]] = {}
        self._sensor_org: dict[UUID, UUID] = {}

    async def load(self) -> None:
        """Fetch all active alert rules from the DB and populate the cache."""
        rules_by_sensor: dict[UUID, list[AlertRuleCached]] = defaultdict(list)
        sensor_org: dict[UUID, UUID] = {}

        async with SQLUnitOfWork(bypass_rls=True) as uow:
            rows = await uow.alert_rule.get_active_with_org()

        for rule_row, organization_id in rows:
            cached = AlertRuleCached(
                id=rule_row.id,
                sensor_id=rule_row.sensor_id,
                condition=rule_row.condition,
                threshold=rule_row.threshold,
                severity=rule_row.severity,
                name=rule_row.name,
            )
            rules_by_sensor[cached.sensor_id].append(cached)
            sensor_org[cached.sensor_id] = organization_id

        self._rules = dict(rules_by_sensor)
        self._sensor_org = sensor_org
        total = sum(len(v) for v in self._rules.values())
        logger.info(
            "Rule cache loaded: {total} rules across {sensors} sensors",
            total=total,
            sensors=len(self._rules),
        )

    def get_rules(self, sensor_id: UUID) -> list[AlertRuleCached]:
        """Return cached rules for a sensor, or an empty list."""
        return self._rules.get(sensor_id, [])

    def get_org_id(self, sensor_id: UUID) -> UUID | None:
        """Return the organization_id for a sensor, or None if not cached."""
        return self._sensor_org.get(sensor_id)

    def get_all_no_data_rules(self) -> list[AlertRuleCached]:
        """Return every cached rule whose condition is NO_DATA."""
        return [
            rule for rules in self._rules.values() for rule in rules if rule.condition == AlertConditionEnum.NO_DATA
        ]

    async def reload(self) -> None:
        """Hot-reload the cache (called from the control-queue subscriber)."""
        logger.info("Rule cache reload triggered")
        await self.load()


rule_cache = RuleCache()
