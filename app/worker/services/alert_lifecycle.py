import time
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any

from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.constants import ALERT_RESOLVE_CONSECUTIVE_OK_READINGS
from app.core.exc import ObjectAlreadyExistsException
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.worker.schemas.telemetry import TelemetryReading
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.common.helpers import is_active_alert_unique_violation, is_update_due, parse_ts
from app.worker.generated import telemetry_pb2
from app.worker.schemas.events import AlertEvent

__all__ = [
    "AlertLifecycleService",
    "alert_lifecycle_service",
    "handle_no_data_recovery",
    "handle_no_data_violation",
    "handle_recovery",
    "handle_violation",
]


def _normalize_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


async def _update_existing_active_alert(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    alert_id: UUID,
    message: str,
    triggered_value: dict[str, Any],
    severity: str,
    state: dict | None,
    now: datetime,
) -> AlertEvent | None:
    emit_update = is_update_due(state, now)

    # Most incoming readings should only refresh Redis state; avoid high-frequency
    # row updates that cause lock contention under concurrent workers.
    if not emit_update:
        await redis_uow.alert_state.set_open(
            sensor_id=sensor_id,
            rule_id=rule_id,
            alert_id=alert_id,
            ok_streak=0,
            last_update_sent_at=parse_ts((state or {}).get("last_update_sent_at")),
        )
        return None

    updated = await uow.alert.update_active_by_id(
        alert_id=alert_id,
        updates={
            "message": message,
            "triggered_value": triggered_value,
        },
    )
    if not updated:
        await redis_uow.alert_state.clear(sensor_id, rule_id)
        return None

    await redis_uow.alert_state.set_open(
        sensor_id=sensor_id,
        rule_id=rule_id,
        alert_id=alert_id,
        ok_streak=0,
        last_update_sent_at=now,
    )

    event: AlertEvent = {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "triggered_value": triggered_value,
        "action": "update",
    }
    return event


class AlertLifecycleService:
    def __init__(
        self,
        sql_uow_factory: type[SQLUnitOfWork] = SQLUnitOfWork,
        rabbitmq_uow_factory: type[RabbitMQUnitOfWork] = RabbitMQUnitOfWork,
    ) -> None:
        self._sql_uow_factory = sql_uow_factory
        self._rabbitmq_uow_factory = rabbitmq_uow_factory

    @staticmethod
    def _apply_control_value(command: telemetry_pb2.ControlCommand, value: Any) -> bool:  # type: ignore[attr-defined]
        # bool must be checked before int because bool is a subclass of int in Python.
        if isinstance(value, bool):
            command.bool_val = value
            return True
        if isinstance(value, int):
            command.int_val = value
            return True
        if isinstance(value, float):
            command.float_val = value
            return True
        if isinstance(value, str):
            command.str_val = value
            return True
        return False

    async def _dispatch_actions(self, rule_id: UUID, organization_id: UUID, is_trigger: bool) -> None:
        try:
            action_dispatches: list[tuple[UUID, UUID, Any]] = []
            async with self._sql_uow_factory(tenant_id=organization_id) as sql_uow:
                actions = await sql_uow.alert_action.get_multi_without_pagination(rule_id=rule_id)
                for action in actions:
                    payload = action.trigger_payload if is_trigger else action.resolve_payload
                    action_dispatches.append((action.id, action.target_sensor_id, payload))

            if not action_dispatches:
                return

            async with self._rabbitmq_uow_factory() as rabbitmq_uow:
                for action_id, target_sensor_id, payload in action_dispatches:
                    if not payload:
                        continue

                    value = payload.get("value") if isinstance(payload, dict) else None
                    if not isinstance(payload, dict) or "value" not in payload:
                        logger.warning(
                            "Skipping action dispatch with invalid payload format for action={action_id} rule={rule_id}",
                            action_id=action_id,
                            rule_id=rule_id,
                        )
                        continue

                    command = telemetry_pb2.ControlCommand(  # type: ignore[attr-defined]
                        command_id=str(uuid4()),
                        sensor_id=str(target_sensor_id),
                        timestamp=int(time.time() * 1000),
                    )
                    if not self._apply_control_value(command, value):
                        logger.warning(
                            "Skipping action dispatch with unsupported payload value type for action={action_id} rule={rule_id}",
                            action_id=action_id,
                            rule_id=rule_id,
                        )
                        continue

                    await rabbitmq_uow.control.publish_command(
                        organization_id=organization_id,
                        payload=command.SerializeToString(),
                    )
                    logger.info(
                        "Dispatched control command to sensor {sensor_id} for rule {rule_id}",
                        sensor_id=target_sensor_id,
                        rule_id=rule_id,
                    )
        except Exception:
            logger.exception(
                "Failed to dispatch alert actions for rule={rule_id} organization={organization_id}",
                rule_id=rule_id,
                organization_id=organization_id,
            )

    async def process_trigger(
        self,
        uow: SQLUnitOfWork,
        redis_uow: RedisUnitOfWork,
        reading: TelemetryReading,
        rule_id: UUID,
        rule_name: str,
        condition: str,
        value: bool | int | float | str,
        threshold: dict[str, Any],
        severity: str,
        organization_id: UUID | None,
    ) -> AlertEvent | None:
        now = datetime.now(timezone.utc)
        sensor_id = reading["sensor_id"]
        triggered_value = dict(reading["payload"])
        state = await redis_uow.alert_state.get_state(sensor_id, rule_id)
        active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
        message = f"Rule '{rule_name}': {condition} triggered (value={value}, threshold={threshold})"

        if active_alert is not None:
            return await _update_existing_active_alert(
                uow=uow,
                redis_uow=redis_uow,
                sensor_id=sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                message=message,
                triggered_value=triggered_value,
                severity=severity,
                state=state,
                now=now,
            )

        try:
            async with uow.session.begin_nested():
                created = await uow.alert.create(
                    {
                        "organization_id": organization_id,
                        "sensor_id": sensor_id,
                        "rule_id": rule_id,
                        "message": message,
                        "triggered_value": triggered_value,
                        "is_acknowledged": False,
                    }
                )
        except (IntegrityError, ObjectAlreadyExistsException) as exc:
            if not is_active_alert_unique_violation(exc):
                raise

            active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
            if active_alert is None:
                raise

            return await _update_existing_active_alert(
                uow=uow,
                redis_uow=redis_uow,
                sensor_id=sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                message=message,
                triggered_value=triggered_value,
                severity=severity,
                state=state,
                now=now,
            )

        await redis_uow.alert_state.set_open(
            sensor_id=sensor_id,
            rule_id=rule_id,
            alert_id=created.id,
            ok_streak=0,
            last_update_sent_at=now,
        )
        if organization_id is not None:
            await self._dispatch_actions(rule_id=rule_id, organization_id=organization_id, is_trigger=True)
        else:
            logger.warning(
                "Skipping trigger action dispatch: missing organization mapping for sensor={sensor_id}",
                sensor_id=sensor_id,
            )

        event: AlertEvent = {
            "sensor_id": sensor_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "triggered_value": triggered_value,
            "action": "open",
        }
        return event

    async def process_resolve(
        self,
        uow: SQLUnitOfWork,
        redis_uow: RedisUnitOfWork,
        sensor_id: UUID,
        rule_id: UUID,
        severity: str,
        organization_id: UUID | None,
    ) -> AlertEvent | None:
        active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
        if active_alert is None:
            await redis_uow.alert_state.clear(sensor_id, rule_id)
            return None

        now = datetime.now(timezone.utc)
        resolved = await uow.alert.resolve_by_id_if_active(active_alert.id, now)
        await redis_uow.alert_state.clear(sensor_id, rule_id)
        if not resolved:
            return None

        if organization_id is not None:
            await self._dispatch_actions(rule_id=rule_id, organization_id=organization_id, is_trigger=False)
        else:
            logger.warning(
                "Skipping resolve action dispatch: missing organization mapping for sensor={sensor_id}",
                sensor_id=sensor_id,
            )

        event: AlertEvent = {
            "sensor_id": sensor_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": active_alert.message,
            "triggered_value": _normalize_payload(active_alert.triggered_value),
            "action": "resolve",
        }
        return event

    async def process_no_data_resolve(
        self,
        uow: SQLUnitOfWork,
        redis_uow: RedisUnitOfWork,
        sensor_id: UUID,
        rule_id: UUID,
        severity: str,
        organization_id: UUID | None,
    ) -> AlertEvent | None:
        active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
        if active_alert is None:
            await redis_uow.alert_state.clear(sensor_id, rule_id)
            return None

        state = await redis_uow.alert_state.get_state(sensor_id, rule_id)
        ok_streak = (state or {}).get("ok_streak", 0) + 1
        if ok_streak < ALERT_RESOLVE_CONSECUTIVE_OK_READINGS:
            await redis_uow.alert_state.set_open(
                sensor_id=sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                ok_streak=ok_streak,
                last_update_sent_at=parse_ts((state or {}).get("last_update_sent_at")),
            )
            return None

        now = datetime.now(timezone.utc)
        resolved = await uow.alert.resolve_by_id_if_active(active_alert.id, now)
        await redis_uow.alert_state.clear(sensor_id, rule_id)
        if not resolved:
            return None

        if organization_id is not None:
            await self._dispatch_actions(rule_id=rule_id, organization_id=organization_id, is_trigger=False)
        else:
            logger.warning(
                "Skipping resolve action dispatch: missing organization mapping for sensor={sensor_id}",
                sensor_id=sensor_id,
            )

        event: AlertEvent = {
            "sensor_id": sensor_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": active_alert.message,
            "triggered_value": _normalize_payload(active_alert.triggered_value),
            "action": "resolve",
        }
        return event

    async def process_no_data_trigger(
        self,
        uow: SQLUnitOfWork,
        redis_uow: RedisUnitOfWork,
        sensor_id: UUID,
        rule_id: UUID,
        rule_name: str,
        severity: str,
        timeout_seconds: int | float,
        organization_id: UUID | None,
    ) -> AlertEvent | None:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {"timeout_seconds": timeout_seconds}
        message = f"Rule '{rule_name}': no data received for >{timeout_seconds}s"
        state = await redis_uow.alert_state.get_state(sensor_id, rule_id)
        active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)

        if active_alert is not None:
            return await _update_existing_active_alert(
                uow=uow,
                redis_uow=redis_uow,
                sensor_id=sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                message=message,
                triggered_value=payload,
                severity=severity,
                state=state,
                now=now,
            )

        try:
            async with uow.session.begin_nested():
                created = await uow.alert.create(
                    {
                        "organization_id": organization_id,
                        "sensor_id": sensor_id,
                        "rule_id": rule_id,
                        "message": message,
                        "triggered_value": payload,
                        "is_acknowledged": False,
                    }
                )
        except (IntegrityError, ObjectAlreadyExistsException) as exc:
            if not is_active_alert_unique_violation(exc):
                raise

            active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
            if active_alert is None:
                raise

            return await _update_existing_active_alert(
                uow=uow,
                redis_uow=redis_uow,
                sensor_id=sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                message=message,
                triggered_value=payload,
                severity=severity,
                state=state,
                now=now,
            )

        await redis_uow.alert_state.set_open(
            sensor_id=sensor_id,
            rule_id=rule_id,
            alert_id=created.id,
            ok_streak=0,
            last_update_sent_at=now,
        )
        if organization_id is not None:
            await self._dispatch_actions(rule_id=rule_id, organization_id=organization_id, is_trigger=True)
        else:
            logger.warning(
                "Skipping trigger action dispatch: missing organization mapping for sensor={sensor_id}",
                sensor_id=sensor_id,
            )

        event: AlertEvent = {
            "sensor_id": sensor_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "triggered_value": payload,
            "action": "open",
        }
        return event


alert_lifecycle_service = AlertLifecycleService()


async def handle_violation(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    reading: TelemetryReading,
    rule_id: UUID,
    rule_name: str,
    condition: str,
    value: bool | int | float | str,
    threshold: dict[str, Any],
    severity: str,
    organization_id: UUID | None,
) -> AlertEvent | None:
    return await alert_lifecycle_service.process_trigger(
        uow=uow,
        redis_uow=redis_uow,
        reading=reading,
        rule_id=rule_id,
        rule_name=rule_name,
        condition=condition,
        value=value,
        threshold=threshold,
        severity=severity,
        organization_id=organization_id,
    )


async def handle_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
    organization_id: UUID | None,
) -> AlertEvent | None:
    return await alert_lifecycle_service.process_resolve(
        uow=uow,
        redis_uow=redis_uow,
        sensor_id=sensor_id,
        rule_id=rule_id,
        severity=severity,
        organization_id=organization_id,
    )


async def handle_no_data_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
    organization_id: UUID | None,
) -> AlertEvent | None:
    return await alert_lifecycle_service.process_no_data_resolve(
        uow=uow,
        redis_uow=redis_uow,
        sensor_id=sensor_id,
        rule_id=rule_id,
        severity=severity,
        organization_id=organization_id,
    )


async def handle_no_data_violation(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    rule_name: str,
    severity: str,
    timeout_seconds: int | float,
    organization_id: UUID | None,
) -> AlertEvent | None:
    return await alert_lifecycle_service.process_no_data_trigger(
        uow=uow,
        redis_uow=redis_uow,
        sensor_id=sensor_id,
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        timeout_seconds=timeout_seconds,
        organization_id=organization_id,
    )
