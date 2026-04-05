import binascii
import re
import secrets
from base64 import b64decode
from datetime import datetime, timezone
from uuid import UUID

from app.core.constants import DEFAULT_CODE_LENGTH

NODE_ID_PATTERN = re.compile(r"^(?:ns=(?P<ns>\d+);)?(?P<type>[isgb])=(?P<val>.+)$")


def generate_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a random numeric code of specified length."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_opc_ua_node_id(value: str) -> str:
    """Validate OPC UA Node ID text (e.g. ``ns=2;s=MyVariable`` or ``i=84``)."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("Node ID cannot be empty.")

    match = NODE_ID_PATTERN.match(normalized)
    if not match:
        raise ValueError("Invalid OPC UA Node ID format.")

    ns_str = match.group("ns")
    id_type = match.group("type")
    id_val = match.group("val")

    # Validate Namespace (UInt16)
    if ns_str is not None:
        ns_idx = int(ns_str)
        if not (0 <= ns_idx <= 65535):
            raise ValueError("Namespace index must be a 16-bit integer (0-65535).")

    match id_type:
        case "i":
            # Validate identifier type and value
            if not id_val.isdigit():
                raise ValueError("Numeric identifier (i=) must be a non-negative integer.")
            if not (0 <= int(id_val) <= 4_294_967_295):
                raise ValueError("Numeric identifier (i=) must be a 32-bit unsigned integer (0-4294967295).")

        case "s":
            if not id_val:
                # Usually strings shouldn't be empty, but the specification is lenient here
                raise ValueError("String identifier (s=) cannot be empty.")

        case "g":
            try:
                UUID(id_val)
            except ValueError as exc:
                raise ValueError("GUID identifier (g=) must be a valid UUID string.") from exc

        case "b":
            try:
                b64decode(id_val, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Byte string identifier (b=) must be valid base64.") from exc

        case _:
            raise ValueError(f"Unknown identifier type: {id_type}")

    return normalized
