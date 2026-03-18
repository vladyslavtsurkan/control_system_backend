from app.enums import AlertConditionEnum
from app.schemas.worker import TelemetryReading
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.cache.rule_cache import rule_cache
from app.worker.common.helpers import extract_typed_values
from app.worker.core.retry import run_with_db_retries
from app.worker.engine import check_condition
from app.worker.schemas.events import AlertEvent, ReadingWrite
from app.worker.services.alert_lifecycle import handle_no_data_recovery, handle_recovery, handle_violation
from app.worker.services.event_publisher import dispatch_alert_notifications, publish_batch_events

__all__ = ["process_telemetry_batch"]


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
            ordered_batch = sorted(batch, key=lambda r: (str(r.sensor_id), r.time))
            for reading in ordered_batch:
                scalar_value, val_num, val_bool, val_str = extract_typed_values(reading.payload.value)
                reading_rows.append(
                    {
                        "time": reading.time,
                        "sensor_id": reading.sensor_id,
                        "val_num": val_num,
                        "val_bool": val_bool,
                        "val_str": val_str,
                        "payload": reading.payload.model_dump(),
                    }
                )

                rules = sorted(rule_cache.get_rules(reading.sensor_id), key=lambda r: str(r.id))
                for rule in rules:
                    if rule.condition == AlertConditionEnum.no_data:
                        event = await handle_no_data_recovery(
                            uow=uow,
                            redis_uow=redis_uow,
                            sensor_id=reading.sensor_id,
                            rule_id=rule.id,
                            severity=rule.severity.value,
                        )
                    elif check_condition(rule.condition, scalar_value, rule.threshold):
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
                    else:
                        event = await handle_recovery(
                            uow=uow,
                            redis_uow=redis_uow,
                            sensor_id=reading.sensor_id,
                            rule_id=rule.id,
                            severity=rule.severity.value,
                        )

                    if event is not None:
                        alert_events.append(event)

            if reading_rows:
                await uow.reading.create_many(reading_rows)

    return reading_rows, alert_events
