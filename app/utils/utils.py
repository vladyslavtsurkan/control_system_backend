import secrets
from datetime import datetime, timezone

from app.core.constants import DEFAULT_CODE_LENGTH


def generate_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a random numeric code of specified length."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
