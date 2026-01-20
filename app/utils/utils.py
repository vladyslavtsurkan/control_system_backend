import secrets

from app.core.constants import DEFAULT_CODE_LENGTH


def generate_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a random numeric code of specified length."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))
