from datetime import datetime, timezone
from itertools import groupby
from uuid import UUID

from app.enums import AlertConditionEnum
from app.worker.schemas.telemetry import TelemetryReading
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.cache.rule_cache import rule_cache
from app.worker.common.helpers import extract_typed_values
from app.worker.core.retry import run_with_db_retries
from app.worker.engine import check_condition
from app.worker.schemas.events import AlertEvent, ReadingWrite
from app.worker.services.alert_lifecycle import handle_no_data_recovery, handle_recovery, handle_violation
from app.worker.services.event_publisher import dispatch_alert_notifications, publish_batch_events

__all__ = ["evaluate_rule_with_debounce", "process_telemetry_batch"]


def _to_unix_ts(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


async def evaluate_rule_with_debounce(
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    condition: AlertConditionEnum,
    threshold: dict,
    duration_seconds: int,
    current_value: bool | int | float | str,
    timestamp: datetime,
) -> tuple[bool, bool]:
    """Evaluate rule violation and debounce state.

    Returns ``(is_violated, should_trigger_alert_now)``.

    Debounce state machine:
    - normal reading -> clear pending timer
    - first violating reading -> set pending first-spike timestamp
    - subsequent violating readings -> trigger only when elapsed >= duration
    """
    is_violated = check_condition(condition, current_value, threshold)
    if not is_violated:
        await redis_uow.alert_state.clear_pending(sensor_id=sensor_id, rule_id=rule_id)
        return False, False

    active_state = await redis_uow.alert_state.get_state(sensor_id=sensor_id, rule_id=rule_id)
    if active_state is not None and active_state.get("status") == "open":
        await redis_uow.alert_state.clear_pending(sensor_id=sensor_id, rule_id=rule_id)
        return True, True

    duration = max(0, int(duration_seconds))
    if duration == 0:
        return True, True

    current_ts = _to_unix_ts(timestamp)
    first_spike_ts = await redis_uow.alert_state.get_pending(sensor_id=sensor_id, rule_id=rule_id)

    if first_spike_ts is None:
        await redis_uow.alert_state.set_pending(
            sensor_id=sensor_id,
            rule_id=rule_id,
            first_spike_ts=current_ts,
            ttl_seconds=duration + 60,
        )
        return True, False

    elapsed_time = current_ts - first_spike_ts
    if elapsed_time < 0:
        # Out-of-order telemetry should reset the baseline instead of instant-firing.
        await redis_uow.alert_state.set_pending(
            sensor_id=sensor_id,
            rule_id=rule_id,
            first_spike_ts=current_ts,
            ttl_seconds=duration + 60,
        )
        return True, False

    if elapsed_time >= duration:
        await redis_uow.alert_state.clear_pending(sensor_id=sensor_id, rule_id=rule_id)
        return True, True

    return True, False


async def process_telemetry_batch(batch: list[TelemetryReading]) -> tuple[int, int]:
    reading_rows, alert_events = await run_with_db_retries(
        operation_name="telemetry batch",
        operation=lambda: _process_telemetry_batch_once(batch),
    )
    dispatch_alert_notifications(alert_events)
    await publish_batch_events(reading_rows, alert_events)
    return len(reading_rows), len(alert_events)


async def _process_telemetry_batch_once(batch: list[TelemetryReading]) -> tuple[list[ReadingWrite], list[AlertEvent]]:
    reading_rows: list[ReadingWrite] = []
    alert_events: list[AlertEvent] = []

    async with RedisUnitOfWork() as redis_uow:
        async with SQLUnitOfWork(bypass_rls=True) as uow:
            # Sort the whole batch by sensor_id + time
            ordered_batch = sorted(batch, key=lambda r: (str(r["sensor_id"]), r["time"]))

            # Group batch by sensor_id
            for sensor_id_str, group in groupby(ordered_batch, key=lambda r: str(r["sensor_id"])):
                sensor_readings = list(group)
                sensor_id = sensor_readings[0]["sensor_id"]

                # 3. Prepare data for insert to DB
                for reading in sensor_readings:
                    scalar_value, val_num, val_bool, val_str = extract_typed_values(reading["payload"]["value"])
                    row: ReadingWrite = {
                        "time": reading["time"],
                        "sensor_id": reading["sensor_id"],
                        "val_num": val_num,
                        "val_bool": val_bool,
                        "val_str": val_str,
                        "payload": dict(reading["payload"]),
                    }
                    reading_rows.append(row)

                # Get rule from cache
                rules = sorted(rule_cache.get_rules(sensor_id), key=lambda r: str(r.id))

                for rule in rules:
                    if rule.condition == AlertConditionEnum.no_data:
                        if sensor_readings:
                            event = await handle_no_data_recovery(
                                uow=uow,
                                redis_uow=redis_uow,
                                sensor_id=sensor_id,
                                rule_id=rule.id,
                                severity=rule.severity.value,
                            )
                            if event is not None:
                                alert_events.append(event)
                        continue

                    for reading in sensor_readings:
                        scalar_value, _, _, _ = extract_typed_values(reading["payload"]["value"])

                        is_violated, should_trigger = await evaluate_rule_with_debounce(
                            redis_uow=redis_uow,
                            sensor_id=sensor_id,
                            rule_id=rule.id,
                            condition=rule.condition,
                            threshold=rule.threshold,
                            duration_seconds=rule.duration_seconds,
                            current_value=scalar_value,
                            timestamp=reading["time"],
                        )

                        if should_trigger:
                            event = await handle_violation(
                                uow=uow,
                                redis_uow=redis_uow,
                                reading=reading,
                                rule_id=rule.id,
                                rule_name=rule.name,
                                condition=rule.condition.value,
                                value=scalar_value,
                                threshold=rule.threshold,
                                severity=rule.severity.value,
                            )
                        elif not is_violated:
                            event = await handle_recovery(
                                uow=uow,
                                redis_uow=redis_uow,
                                sensor_id=sensor_id,
                                rule_id=rule.id,
                                severity=rule.severity.value,
                            )
                        else:
                            event = None

                        if event is not None:
                            alert_events.append(event)

            if reading_rows:
                await uow.reading.create_many(reading_rows)

    return reading_rows, alert_events
