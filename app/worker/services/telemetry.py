from datetime import datetime, timezone
from itertools import groupby
from uuid import UUID

from app.enums import AlertConditionEnum
from app.worker.schemas.telemetry import TelemetryReading
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.services.rule_cache import rule_cache_service
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


def evaluate_rule_with_debounce(
    sensor_id: UUID,
    rule_id: UUID,
    condition: AlertConditionEnum,
    threshold: dict,
    duration_seconds: int,
    current_value: bool | int | float | str,
    timestamp: datetime,
    active_state: dict | None,
    pending_ts: float | None,
) -> tuple[bool, bool, float | None, bool]:
    """Evaluate rule violation and debounce state.

    Returns ``(is_violated, should_trigger_alert_now, next_pending_ts, pending_state_mutated)``.

    Debounce state machine:
    - normal reading -> clear pending timer
    - first violating reading -> set pending first-spike timestamp
    - subsequent violating readings -> trigger only when elapsed >= duration
    """
    # Keep signature aligned with call sites keyed by sensor+rule.
    _ = (sensor_id, rule_id)

    is_violated = check_condition(condition, current_value, threshold)
    if not is_violated:
        return False, False, None, pending_ts is not None

    if active_state is not None and active_state.get("status") == "open":
        return True, True, None, pending_ts is not None

    duration = max(0, int(duration_seconds))
    if duration == 0:
        return True, True, None, pending_ts is not None

    current_ts = _to_unix_ts(timestamp)
    if pending_ts is None:
        return True, False, current_ts, True

    elapsed_time = current_ts - pending_ts
    if elapsed_time < 0:
        # Out-of-order telemetry should reset the baseline instead of instant-firing.
        return True, False, current_ts, pending_ts != current_ts

    if elapsed_time >= duration:
        return True, True, None, True

    return True, False, pending_ts, False


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
                rules = sorted(rule_cache_service.get_rules(sensor_id), key=lambda r: str(r.id))

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

                    active_state = await redis_uow.alert_state.get_state(sensor_id=sensor_id, rule_id=rule.id)
                    pending_ts = await redis_uow.alert_state.get_pending(sensor_id=sensor_id, rule_id=rule.id)
                    pending_mutated = False

                    for reading in sensor_readings:
                        scalar_value, _, _, _ = extract_typed_values(reading["payload"]["value"])

                        is_violated, should_trigger, pending_ts, pending_state_mutated = evaluate_rule_with_debounce(
                            sensor_id=sensor_id,
                            rule_id=rule.id,
                            condition=rule.condition,
                            threshold=rule.threshold,
                            duration_seconds=rule.duration_seconds,
                            current_value=scalar_value,
                            timestamp=reading["time"],
                            active_state=active_state,
                            pending_ts=pending_ts,
                        )
                        pending_mutated = pending_mutated or pending_state_mutated

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
                            active_state = {"status": "open"}
                        elif not is_violated:
                            event = await handle_recovery(
                                uow=uow,
                                redis_uow=redis_uow,
                                sensor_id=sensor_id,
                                rule_id=rule.id,
                                severity=rule.severity.value,
                            )
                            active_state = None
                        else:
                            event = None

                        if event is not None:
                            alert_events.append(event)

                    if pending_mutated:
                        if pending_ts is None:
                            await redis_uow.alert_state.clear_pending(sensor_id=sensor_id, rule_id=rule.id)
                        else:
                            await redis_uow.alert_state.set_pending(
                                sensor_id=sensor_id,
                                rule_id=rule.id,
                                first_spike_ts=pending_ts,
                                ttl_seconds=max(0, int(rule.duration_seconds)) + 60,
                            )

            if reading_rows:
                await uow.reading.create_many(reading_rows)

    return reading_rows, alert_events
