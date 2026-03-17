from app.enums import AlertConditionEnum
from app.schemas.worker import TelemetryReading
from app.worker.rule_cache import AlertRuleCached, RuleCache

__all__ = ["check_condition", "evaluate_rules"]


def check_condition(condition: AlertConditionEnum, value: float, threshold: dict) -> bool:
    """
    Evaluate a single condition against a reading value and threshold dict.

    Returns True when the condition is **violated** (i.e. an alert should fire).
    """
    if condition == AlertConditionEnum.greater_than:
        return value > threshold["value"]

    if condition == AlertConditionEnum.less_than:
        return value < threshold["value"]

    if condition == AlertConditionEnum.equals:
        return value == threshold["value"]

    if condition == AlertConditionEnum.not_equals:
        return value != threshold["value"]

    if condition == AlertConditionEnum.outside_range:
        return value < threshold["min"] or value > threshold["max"]

    if condition == AlertConditionEnum.inside_range:
        return threshold["min"] <= value <= threshold["max"]

    # NO_DATA is handled by the background loop, not here.
    return False


def _build_alert_dict(reading: TelemetryReading, rule: AlertRuleCached) -> dict:
    """Build a dict that matches the Alert model columns."""
    return {
        "sensor_id": reading.sensor_id,
        "rule_id": rule.id,
        "message": (
            f"Rule '{rule.name}': {rule.condition.value} triggered "
            f"(value={reading.payload.value}, threshold={rule.threshold})"
        ),
        "triggered_value": reading.payload.model_dump(),
        "is_acknowledged": False,
    }


def evaluate_rules(
    readings: list[TelemetryReading],
    cache: RuleCache,
) -> tuple[list[dict], list[dict]]:
    """
    Evaluate every reading against the in-memory rule cache.

    Returns:
        A tuple of (reading_dicts, alert_dicts) ready for bulk insertion
        via the existing repositories.
    """
    reading_dicts: list[dict] = []
    alert_dicts: list[dict] = []

    for reading in readings:
        reading_dicts.append(
            {
                "time": reading.time,
                "sensor_id": reading.sensor_id,
                "payload": reading.payload.model_dump(),
            }
        )

        rules = cache.get_rules(reading.sensor_id)
        for rule in rules:
            if rule.condition == AlertConditionEnum.no_data:
                continue

            if check_condition(rule.condition, reading.payload.value, rule.threshold):
                alert_dicts.append(_build_alert_dict(reading, rule))

    return reading_dicts, alert_dicts
