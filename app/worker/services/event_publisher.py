import asyncio
from uuid import UUID

from loguru import logger

from app.infra.celery.tasks import send_alert_notification
from app.schemas.ws import WsBroadcastEvent
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.worker.cache.rule_cache import rule_cache
from app.worker.schemas.events import AlertEvent, ReadingWrite

__all__ = ["dispatch_alert_notifications", "publish_batch_events"]


def dispatch_alert_notifications(alert_events: list[AlertEvent]) -> None:
    for alert in alert_events:
        send_alert_notification.delay(alert)


async def publish_batch_events(
    reading_rows: list[ReadingWrite],
    alert_events: list[AlertEvent],
) -> None:
    events: list[WsBroadcastEvent] = []
    missing_sensor_ids: set[UUID] = set()

    for reading in reading_rows:
        sensor_id = reading["sensor_id"]
        org_id = rule_cache.get_org_id(sensor_id)
        if org_id is None:
            missing_sensor_ids.add(sensor_id)
            continue
        events.append(
            WsBroadcastEvent(
                type="telemetry",
                organization_id=org_id,
                sensor_id=sensor_id,
                data={"time": reading["time"].isoformat(), "payload": reading["payload"]},
            )
        )

    for alert in alert_events:
        sensor_id = alert["sensor_id"]
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
                    "rule_id": str(alert["rule_id"]),
                    "severity": alert["severity"],
                    "action": alert["action"],
                    "message": alert["message"],
                    "triggered_value": alert["triggered_value"],
                },
            )
        )

    for sensor_id in missing_sensor_ids:
        logger.warning("WS broadcast skipped: missing sensor->org mapping for sensor={sensor}", sensor=sensor_id)

    if not events:
        return

    try:
        async with RabbitMQUnitOfWork() as rmq:
            await asyncio.gather(*[rmq.broadcast.publish(event) for event in events])
    except Exception:
        logger.exception("Failed to publish WS broadcast events")
