from datetime import datetime, timezone

from app.core.constants import ALERT_UPDATE_THROTTLE_SECONDS

__all__ = [
    "extract_typed_values",
    "is_active_alert_unique_violation",
    "is_retryable_postgres_error",
    "is_update_due",
    "postgres_sqlstate",
    "parse_ts",
]


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_update_due(state: dict | None, now: datetime) -> bool:
    if state is None:
        return True
    last_update_sent_at = parse_ts(state.get("last_update_sent_at"))
    if last_update_sent_at is None:
        return True
    return (now - last_update_sent_at).total_seconds() >= ALERT_UPDATE_THROTTLE_SECONDS


def is_active_alert_unique_violation(exc: Exception) -> bool:
    current: Exception | None = exc
    while current is not None:
        sqlstate = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
        constraint = getattr(current, "constraint_name", None)
        if sqlstate == "23505" and constraint == "uq_active_alert_per_rule":
            return True

        orig = getattr(current, "orig", None)
        if orig is not None:
            orig_sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            orig_constraint = getattr(orig, "constraint_name", None)
            if orig_sqlstate == "23505" and orig_constraint == "uq_active_alert_per_rule":
                return True

            text = str(orig)
            if "duplicate key value" in text and "uq_active_alert_per_rule" in text:
                return True

        text = str(current)
        if "duplicate key value" in text and "uq_active_alert_per_rule" in text:
            return True

        next_exc = current.__cause__ or current.__context__
        current = next_exc if isinstance(next_exc, Exception) else None

    return False


def postgres_sqlstate(exc: Exception) -> str | None:
    current: Exception | None = exc
    while current is not None:
        sqlstate = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
        if isinstance(sqlstate, str) and sqlstate:
            return sqlstate

        orig = getattr(current, "orig", None)
        if orig is not None:
            orig_sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            if isinstance(orig_sqlstate, str) and orig_sqlstate:
                return orig_sqlstate

        next_exc = current.__cause__ or current.__context__
        current = next_exc if isinstance(next_exc, Exception) else None

    return None


def is_retryable_postgres_error(exc: Exception) -> bool:
    return postgres_sqlstate(exc) in {"40P01", "40001"}


def extract_typed_values(
    value: bool | int | float | str,
) -> tuple[bool | int | float | str, float | None, bool | None, str | None]:
    if isinstance(value, bool):
        return value, None, value, None
    if isinstance(value, (int, float)):
        return value, float(value), None, None
    return value, None, None, value
