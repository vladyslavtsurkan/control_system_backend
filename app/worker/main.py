import asyncio
from datetime import datetime, timezone
from uuid import UUID

from faststream import FastStream
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue
from loguru import logger

from app.core.config import settings
from app.core.constants import DEFAULT_NO_DATA_TIMEOUT_SECONDS
from app.infra.celery.tasks import send_alert_notification
from app.schemas.worker import TelemetryReading
from app.schemas.ws import WsBroadcastEvent
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.engine import evaluate_rules
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
    reading_dicts, alert_dicts = evaluate_rules(batch, rule_cache)

    async with SQLUnitOfWork(bypass_rls=True) as uow:
        if reading_dicts:
            await uow.reading.create_many(reading_dicts)
        if alert_dicts:
            await uow.alert.create_many(alert_dicts)

    # Fire-and-forget Celery tasks *after* the DB transaction has committed
    for alert in alert_dicts:
        send_alert_notification.delay(alert)

    # Publish WS broadcast events — one channel for the entire batch
    await _publish_batch_events(reading_dicts, alert_dicts)

    logger.debug(
        "Batch processed: {readings} readings, {alerts} alerts",
        readings=len(reading_dicts),
        alerts=len(alert_dicts),
    )


async def _publish_batch_events(
    reading_dicts: list[dict],
    alert_dicts: list[dict],
) -> None:
    """Build and publish all WS broadcast events for a telemetry batch.

    All events are published over a *single* RabbitMQ channel that is opened
    once per batch, regardless of batch size, keeping overhead minimal under
    high throughput.  Sensors without a cached org mapping are silently skipped.
    """
    events: list[WsBroadcastEvent] = []

    for r in reading_dicts:
        sensor_id: UUID = r["sensor_id"]
        org_id = rule_cache.get_org_id(sensor_id)
        if org_id is None:
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
            continue
        events.append(
            WsBroadcastEvent(
                type="alert",
                organization_id=org_id,
                sensor_id=sensor_id,
                data={
                    "rule_id": str(a["rule_id"]),
                    "message": a["message"],
                    "triggered_value": a["triggered_value"],
                },
            )
        )

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
            alert_dicts: list[dict] = []

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
                        # Ensure timezone-aware comparison
                        if last_time.tzinfo is None:
                            last_time = last_time.replace(tzinfo=timezone.utc)
                        elapsed = (now - last_time).total_seconds()
                        if elapsed > timeout:
                            is_stale = True

                    if is_stale:
                        alert_dicts.append(
                            {
                                "sensor_id": rule.sensor_id,
                                "rule_id": rule.id,
                                "message": f"Rule '{rule.name}': no data received for >{timeout}s",
                                "triggered_value": {"timeout_seconds": timeout},
                                "is_acknowledged": False,
                            }
                        )

                if alert_dicts:
                    await uow.alert.create_many(alert_dicts)

            # Celery stubs after commit
            for alert in alert_dicts:
                send_alert_notification.delay(alert)

            # WS broadcast for NO_DATA alerts
            await _publish_batch_events([], alert_dicts)

            if alert_dicts:
                logger.info(
                    "NO_DATA check: {count} alerts triggered",
                    count=len(alert_dicts),
                )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in NO_DATA background loop")
