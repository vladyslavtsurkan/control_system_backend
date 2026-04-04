from typing import TypedDict
from uuid import UUID

__all__ = ["PendingMutation"]


class PendingMutation(TypedDict):
    sensor_id: UUID
    rule_id: UUID
    first_spike_ts: float | None
    ttl_seconds: int | None
