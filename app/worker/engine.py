from typing import Any

from app.enums import AlertConditionEnum
from app.schemas.worker import TelemetryReading
from app.worker.rule_cache import AlertRuleCached, RuleCache

__all__ = ["check_condition", "evaluate_rules"]


def check_condition(condition: AlertConditionEnum, value: bool | int | float | str, threshold: dict[str, Any]) -> bool:
    """
    Evaluate a single condition against a reading value and threshold dict.

    Returns True when the condition is **violated** (i.e. an alert should fire).
    """
    is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)

    if condition == AlertConditionEnum.GREATER_THAN:
        if not is_numeric:
            return False
        return value > threshold["value"]

    if condition == AlertConditionEnum.LESS_THAN:
        if not is_numeric:
            return False
        return value < threshold["value"]

    if condition == AlertConditionEnum.EQUALS:
        return value == threshold["value"]

    if condition == AlertConditionEnum.NOT_EQUALS:
        return value != threshold["value"]

    if condition == AlertConditionEnum.OUTSIDE_RANGE:
        if not is_numeric:
            return False
        return value < threshold["min"] or value > threshold["max"]

    if condition == AlertConditionEnum.INSIDE_RANGE:
        if not is_numeric:
            return False
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
        value = reading.payload.value
        val_num: float | None = None
        val_bool: bool | None = None
        val_str: str | None = None
        if isinstance(value, bool):
            val_bool = value
        elif isinstance(value, (int, float)):
            val_num = float(value)
        else:
            val_str = value

        reading_dicts.append(
            {
                "time": reading.time,
                "sensor_id": reading.sensor_id,
                "val_num": val_num,
                "val_bool": val_bool,
                "val_str": val_str,
                "payload": reading.payload.model_dump(),
            }
        )

        rules = cache.get_rules(reading.sensor_id)
        for rule in rules:
            if rule.condition == AlertConditionEnum.NO_DATA:
                continue

            if check_condition(rule.condition, value, rule.threshold):
                alert_dicts.append(_build_alert_dict(reading, rule))

    return reading_dicts, alert_dicts
