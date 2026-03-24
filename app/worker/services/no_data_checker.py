from datetime import datetime, timezone

from app.core.constants import DEFAULT_NO_DATA_TIMEOUT_SECONDS
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.services.rule_cache import rule_cache_service
from app.worker.core.retry import run_with_db_retries
from app.worker.schemas.events import AlertEvent
from app.worker.services.alert_lifecycle import handle_no_data_violation
from app.worker.services.event_publisher import dispatch_alert_notifications, publish_batch_events

__all__ = ["run_no_data_check"]


async def run_no_data_check() -> int:
    alert_events = await run_with_db_retries(
        operation_name="no_data check",
        operation=_run_no_data_check_once,
    )
    dispatch_alert_notifications(alert_events)
    await publish_batch_events([], alert_events)
    return len(alert_events)


async def _run_no_data_check_once() -> list[AlertEvent]:
    no_data_rules = sorted(rule_cache_service.get_all_no_data_rules(), key=lambda r: (str(r.sensor_id), str(r.id)))
    if not no_data_rules:
        return []

    now = datetime.now(timezone.utc)
    alert_events: list[AlertEvent] = []

    async with RedisUnitOfWork() as redis_uow:
        async with SQLUnitOfWork(bypass_rls=True) as uow:
            for rule in no_data_rules:
                readings, _ = await uow.reading.get_multi(
                    sensor_id=rule.sensor_id,
                    limit=1,
                    order_by="-time",
                )
                timeout = rule.threshold.get("timeout_seconds", DEFAULT_NO_DATA_TIMEOUT_SECONDS)

                if readings:
                    last_time = readings[0].time
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=timezone.utc)
                    elapsed = (now - last_time).total_seconds()
                    if elapsed <= timeout:
                        continue

                event = await handle_no_data_violation(
                    uow=uow,
                    redis_uow=redis_uow,
                    sensor_id=rule.sensor_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity.value,
                    timeout_seconds=timeout,
                )
                if event is not None:
                    alert_events.append(event)

    return alert_events
