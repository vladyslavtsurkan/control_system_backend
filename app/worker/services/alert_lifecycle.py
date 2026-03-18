from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.constants import ALERT_RESOLVE_CONSECUTIVE_OK_READINGS
from app.core.exc import ObjectAlreadyExistsException
from app.schemas.worker import TelemetryReading
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.common.helpers import is_active_alert_unique_violation, is_update_due, parse_ts
from app.worker.schemas.events import AlertEvent

__all__ = [
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
) -> AlertEvent | None:
    now = datetime.now(timezone.utc)
    sensor_id = reading.sensor_id
    triggered_value = reading.payload.model_dump()
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
    event: AlertEvent = {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "triggered_value": triggered_value,
        "action": "open",
    }
    return event


async def handle_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
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

    event: AlertEvent = {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": active_alert.message,
        "triggered_value": _normalize_payload(active_alert.triggered_value),
        "action": "resolve",
    }
    return event


async def handle_no_data_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
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

    event: AlertEvent = {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": active_alert.message,
        "triggered_value": _normalize_payload(active_alert.triggered_value),
        "action": "resolve",
    }
    return event


async def handle_no_data_violation(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    rule_name: str,
    severity: str,
    timeout_seconds: int | float,
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
    event: AlertEvent = {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "triggered_value": payload,
        "action": "open",
    }
    return event
