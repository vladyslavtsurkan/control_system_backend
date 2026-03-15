import asyncio
from datetime import datetime, timezone
from uuid import UUID

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import (
    ALERT_RESOLVE_CONSECUTIVE_OK_READINGS,
    ALERT_UPDATE_THROTTLE_SECONDS,
    DEFAULT_NO_DATA_TIMEOUT_SECONDS,
)
from app.infra.celery.tasks import send_alert_notification
from app.enums import AlertConditionEnum
from app.schemas.worker import TelemetryReading
from app.schemas.ws import WsBroadcastEvent
from app.uow.redis import RedisUnitOfWork
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.engine import check_condition
from app.worker.rule_cache import rule_cache

broker = RabbitBroker(settings.rabbitmq.url)
app = FastStream(broker)

telemetry_exchange = RabbitExchange(
    settings.rabbitmq.TELEMETRY_EXCHANGE,
    type=ExchangeType.TOPIC,
    durable=True,
)
telemetry_queue = RabbitQueue(
    settings.rabbitmq.TELEMETRY_QUEUE,
    durable=True,
    routing_key=settings.rabbitmq.TELEMETRY_ROUTING_KEY,
)

control_exchange = RabbitExchange(
    settings.rabbitmq.CONTROL_EXCHANGE,
    type=ExchangeType.FANOUT,
    durable=True,
)
control_queue = RabbitQueue(
    settings.rabbitmq.CONTROL_QUEUE,
    durable=True,
)

_no_data_task: asyncio.Task | None = None


@app.on_startup
async def on_startup() -> None:
    global _no_data_task

    logger.info("Worker starting — loading rule cache …")
    await rule_cache.load()

    _no_data_task = asyncio.create_task(_no_data_loop())
    logger.info("NO_DATA background checker started")


@app.on_shutdown
async def on_shutdown() -> None:
    if _no_data_task is not None:
        _no_data_task.cancel()
        try:
            await _no_data_task
        except asyncio.CancelledError:
            pass
    logger.info("Worker shut down gracefully")


@broker.subscriber(telemetry_queue, telemetry_exchange)
async def handle_telemetry(batch: list[TelemetryReading]) -> None:
    """Process an incoming batch of telemetry readings.

    1. Evaluate rules in-memory.
    2. Bulk-insert readings + alerts in a single atomic transaction.
    3. Dispatch Celery notification stubs for every triggered alert.
    4. Publish WS broadcast events (telemetry + alert) over one shared channel.
    """
    reading_dicts: list[dict] = []
    alert_events: list[dict] = []

    async with RedisUnitOfWork() as redis_uow:
        async with SQLUnitOfWork(bypass_rls=True) as uow:
            for reading in batch:
                reading_dicts.append(
                    {
                        "time": reading.time,
                        "sensor_id": reading.sensor_id,
                        "payload": reading.payload.model_dump(),
                    }
                )

                rules = rule_cache.get_rules(reading.sensor_id)
                for rule in rules:
                    if rule.condition == AlertConditionEnum.NO_DATA:
                        event = await _handle_no_data_recovery(
                            uow,
                            redis_uow,
                            reading.sensor_id,
                            rule.id,
                            rule.severity.value,
                        )
                        if event is not None:
                            alert_events.append(event)
                        continue

                    is_violated = check_condition(rule.condition, reading.payload.value, rule.threshold)
                    if is_violated:
                        event = await _handle_violation(
                            uow=uow,
                            redis_uow=redis_uow,
                            reading=reading,
                            rule_id=rule.id,
                            rule_name=rule.name,
                            condition=rule.condition.value,
                            threshold=rule.threshold,
                            severity=rule.severity.value,
                        )
                    else:
                        event = await _handle_recovery(
                            uow=uow,
                            redis_uow=redis_uow,
                            sensor_id=reading.sensor_id,
                            rule_id=rule.id,
                            severity=rule.severity.value,
                        )

                    if event is not None:
                        alert_events.append(event)

            if reading_dicts:
                await uow.reading.create_many(reading_dicts)

    # Fire-and-forget Celery tasks *after* the DB transaction has committed
    for alert in alert_events:
        send_alert_notification.delay(alert)

    # Publish WS broadcast events — one channel for the entire batch
    await _publish_batch_events(reading_dicts, alert_events)

    logger.debug(
        "Batch processed: {readings} readings, {alerts} alerts",
        readings=len(reading_dicts),
        alerts=len(alert_events),
    )


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_update_due(state: dict | None, now: datetime) -> bool:
    if state is None:
        return True
    last_update_sent_at = _parse_ts(state.get("last_update_sent_at"))
    if last_update_sent_at is None:
        return True
    return (now - last_update_sent_at).total_seconds() >= ALERT_UPDATE_THROTTLE_SECONDS


async def _handle_violation(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    reading: TelemetryReading,
    rule_id: UUID,
    rule_name: str,
    condition: str,
    threshold: dict,
    severity: str,
) -> dict | None:
    now = datetime.now(timezone.utc)
    state = await redis_uow.alert_state.get_state(reading.sensor_id, rule_id)
    active_alert = await uow.alert.get_active_by_sensor_rule(reading.sensor_id, rule_id)
    message = f"Rule '{rule_name}': {condition} triggered (value={reading.payload.value}, threshold={threshold})"

    if active_alert is None:
        try:
            created = await uow.alert.create(
                {
                    "sensor_id": reading.sensor_id,
                    "rule_id": rule_id,
                    "message": message,
                    "triggered_value": reading.payload.model_dump(),
                    "is_acknowledged": False,
                }
            )
        except IntegrityError:
            # Another worker created the active alert first; reuse it.
            active_alert = await uow.alert.get_active_by_sensor_rule(reading.sensor_id, rule_id)
            if active_alert is None:
                raise
            await uow.alert.update(
                filters={"id": active_alert.id},
                updates={
                    "message": message,
                    "triggered_value": reading.payload.model_dump(),
                },
            )
            emit_update = _is_update_due(state, now)
            await redis_uow.alert_state.set_open(
                sensor_id=reading.sensor_id,
                rule_id=rule_id,
                alert_id=active_alert.id,
                ok_streak=0,
                last_update_sent_at=now if emit_update else _parse_ts((state or {}).get("last_update_sent_at")),
            )
            if not emit_update:
                return None
            return {
                "sensor_id": reading.sensor_id,
                "rule_id": rule_id,
                "severity": severity,
                "message": message,
                "triggered_value": reading.payload.model_dump(),
                "action": "update",
            }

        await redis_uow.alert_state.set_open(
            sensor_id=reading.sensor_id,
            rule_id=rule_id,
            alert_id=created.id,
            ok_streak=0,
            last_update_sent_at=now,
        )
        return {
            "sensor_id": reading.sensor_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "triggered_value": reading.payload.model_dump(),
            "action": "open",
        }

    await uow.alert.update(
        filters={"id": active_alert.id},
        updates={
            "message": message,
            "triggered_value": reading.payload.model_dump(),
        },
    )

    emit_update = _is_update_due(state, now)
    await redis_uow.alert_state.set_open(
        sensor_id=reading.sensor_id,
        rule_id=rule_id,
        alert_id=active_alert.id,
        ok_streak=0,
        last_update_sent_at=now if emit_update else _parse_ts((state or {}).get("last_update_sent_at")),
    )

    if not emit_update:
        return None

    return {
        "sensor_id": reading.sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "triggered_value": reading.payload.model_dump(),
        "action": "update",
    }


async def _handle_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
) -> dict | None:
    active_alert = await uow.alert.get_active_by_sensor_rule(sensor_id, rule_id)
    if active_alert is None:
        await redis_uow.alert_state.clear(sensor_id, rule_id)
        return None

    now = datetime.now(timezone.utc)
    await uow.alert.update(filters={"id": active_alert.id}, updates={"resolved_at": now})
    await redis_uow.alert_state.clear(sensor_id, rule_id)

    return {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": active_alert.message,
        "triggered_value": active_alert.triggered_value,
        "action": "resolve",
    }


async def _handle_no_data_recovery(
    uow: SQLUnitOfWork,
    redis_uow: RedisUnitOfWork,
    sensor_id: UUID,
    rule_id: UUID,
    severity: str,
) -> dict | None:
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
            last_update_sent_at=_parse_ts((state or {}).get("last_update_sent_at")),
        )
        return None

    now = datetime.now(timezone.utc)
    await uow.alert.update(filters={"id": active_alert.id}, updates={"resolved_at": now})
    await redis_uow.alert_state.clear(sensor_id, rule_id)
    return {
        "sensor_id": sensor_id,
        "rule_id": rule_id,
        "severity": severity,
        "message": active_alert.message,
        "triggered_value": active_alert.triggered_value,
        "action": "resolve",
    }


async def _publish_batch_events(
    reading_dicts: list[dict],
    alert_dicts: list[dict],
) -> None:
    """Build and publish all WS broadcast events for a telemetry batch.

    All events are published over a *single* RabbitMQ channel that is opened
    once per batch, regardless of batch size, keeping overhead minimal under
    high throughput.  Sensors without a cached org mapping are skipped and
    logged so ingestion/routing issues are visible in production.
    """
    events: list[WsBroadcastEvent] = []
    missing_sensor_ids: set[UUID] = set()

    for r in reading_dicts:
        sensor_id: UUID = r["sensor_id"]
        org_id = rule_cache.get_org_id(sensor_id)
        if org_id is None:
            missing_sensor_ids.add(sensor_id)
            continue
        events.append(
            WsBroadcastEvent(
                type="telemetry",
                organization_id=org_id,
                sensor_id=sensor_id,
                data={"time": r["time"].isoformat(), "payload": r["payload"]},
            )
        )

    for a in alert_dicts:
        sensor_id = a["sensor_id"]
        org_id = rule_cache.get_org_id(sensor_id)
        if org_id is None:
            missing_sensor_ids.add(sensor_id)
            continue
        events.append(
            WsBroadcastEvent(
                type="alert",
                organization_id=org_id,
                sensor_id=sensor_id,
                data={
                    "rule_id": str(a["rule_id"]),
                    "severity": a.get("severity"),
                    "action": a.get("action", "open"),
                    "message": a["message"],
                    "triggered_value": a["triggered_value"],
                },
            )
        )

    for sensor_id in missing_sensor_ids:
        logger.warning("WS broadcast skipped: missing sensor->org mapping for sensor={sensor}", sensor=sensor_id)

    if not events:
        return

    try:
        async with RabbitMQUnitOfWork() as rmq:
            await asyncio.gather(*[rmq.broadcast.publish(e) for e in events])
    except Exception:
        logger.exception("Failed to publish WS broadcast events")


@broker.subscriber(control_queue, control_exchange)
async def handle_control(msg: str) -> None:
    """Hot-reload the rule cache when the Control Plane mutates alert rules."""
    logger.info("Control message received: {msg}", msg=msg)
    await rule_cache.reload()


async def _no_data_loop() -> None:
    """Periodically check for sensors that stopped reporting data.

    For every active NO_DATA rule, fetch the most recent reading
    and trigger an alert if it is older than the configured timeout.
    """
    interval = settings.rabbitmq.NO_DATA_CHECK_INTERVAL_SECONDS

    while True:
        await asyncio.sleep(interval)
        try:
            no_data_rules = rule_cache.get_all_no_data_rules()
            if not no_data_rules:
                continue

            now = datetime.now(timezone.utc)
            alert_events: list[dict] = []

            async with RedisUnitOfWork() as redis_uow:
                async with SQLUnitOfWork(bypass_rls=True) as uow:
                    for rule in no_data_rules:
                        readings, _ = await uow.reading.get_multi(
                            sensor_id=rule.sensor_id,
                            limit=1,
                            order_by="-time",
                        )
                        timeout = rule.threshold.get("timeout_seconds", DEFAULT_NO_DATA_TIMEOUT_SECONDS)

                        is_stale = False
                        if not readings:
                            is_stale = True
                        else:
                            last_time = readings[0].time
                            if last_time.tzinfo is None:
                                last_time = last_time.replace(tzinfo=timezone.utc)
                            elapsed = (now - last_time).total_seconds()
                            if elapsed > timeout:
                                is_stale = True

                        if not is_stale:
                            continue

                        message = f"Rule '{rule.name}': no data received for >{timeout}s"
                        payload = {"timeout_seconds": timeout}
                        state = await redis_uow.alert_state.get_state(rule.sensor_id, rule.id)
                        active_alert = await uow.alert.get_active_by_sensor_rule(rule.sensor_id, rule.id)

                        if active_alert is None:
                            created = await uow.alert.create(
                                {
                                    "sensor_id": rule.sensor_id,
                                    "rule_id": rule.id,
                                    "message": message,
                                    "triggered_value": payload,
                                    "is_acknowledged": False,
                                }
                            )
                            await redis_uow.alert_state.set_open(
                                sensor_id=rule.sensor_id,
                                rule_id=rule.id,
                                alert_id=created.id,
                                ok_streak=0,
                                last_update_sent_at=now,
                            )
                            alert_events.append(
                                {
                                    "sensor_id": rule.sensor_id,
                                    "rule_id": rule.id,
                                    "severity": rule.severity.value,
                                    "message": message,
                                    "triggered_value": payload,
                                    "action": "open",
                                }
                            )
                            continue

                        await uow.alert.update(
                            filters={"id": active_alert.id},
                            updates={"message": message, "triggered_value": payload},
                        )

                        emit_update = _is_update_due(state, now)
                        await redis_uow.alert_state.set_open(
                            sensor_id=rule.sensor_id,
                            rule_id=rule.id,
                            alert_id=active_alert.id,
                            ok_streak=0,
                            last_update_sent_at=now
                            if emit_update
                            else _parse_ts((state or {}).get("last_update_sent_at")),
                        )

                        if emit_update:
                            alert_events.append(
                                {
                                    "sensor_id": rule.sensor_id,
                                    "rule_id": rule.id,
                                    "severity": rule.severity.value,
                                    "message": message,
                                    "triggered_value": payload,
                                    "action": "update",
                                }
                            )

            # Celery stubs after commit
            for alert in alert_events:
                send_alert_notification.delay(alert)

            # WS broadcast for NO_DATA alerts
            await _publish_batch_events([], alert_events)

            if alert_events:
                logger.info(
                    "NO_DATA check: {count} alerts triggered",
                    count=len(alert_events),
                )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in NO_DATA background loop")
