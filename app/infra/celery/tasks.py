from loguru import logger

from app.infra.celery.app import celery_app

__all__ = ["send_alert_notification"]


@celery_app.task(name="send_alert_notification")
def send_alert_notification(alert_data: dict) -> None:
    """Stub task for sending alert notifications.

    In production this would dispatch emails, SMS, webhooks, etc.
    Currently, logs the alert payload and returns.
    """
    logger.info(
        "Would send notification for alert | sensor_id={sensor_id} rule_id={rule_id} message={message}",
        sensor_id=alert_data.get("sensor_id"),
        rule_id=alert_data.get("rule_id"),
        message=alert_data.get("message"),
    )
