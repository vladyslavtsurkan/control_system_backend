from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.repositories.redis.base import BaseRedisRepository

__all__ = ["AlertStateRepository"]

ALERT_STATE_KEY = "alert_state:{sensor_id}:{rule_id}"


class AlertStateRepository(BaseRedisRepository):
    """Stores transient alert lifecycle state per ``sensor_id + rule_id``.

    This state is intentionally ephemeral; if Redis is flushed, the worker
    rebuilds state from subsequent telemetry messages.
    """

    @staticmethod
    def _key(sensor_id: UUID, rule_id: UUID) -> str:
        return ALERT_STATE_KEY.format(sensor_id=sensor_id, rule_id=rule_id)

    async def get_state(self, sensor_id: UUID, rule_id: UUID) -> dict | None:
        state = await self.get(self._key(sensor_id, rule_id))
        if state is None:
            return None

        return {
            "alert_id": state.get("alert_id"),
            "status": state.get("status", "open"),
            "ok_streak": int(state.get("ok_streak", "0")),
            "last_update_sent_at": state.get("last_update_sent_at"),
        }

    async def set_open(
        self,
        sensor_id: UUID,
        rule_id: UUID,
        alert_id: UUID,
        ok_streak: int = 0,
        last_update_sent_at: datetime | None = None,
    ) -> None:
        payload = {
            "alert_id": str(alert_id),
            "status": "open",
            "ok_streak": str(ok_streak),
            "last_update_sent_at": last_update_sent_at.isoformat() if last_update_sent_at else "",
        }
        await self.set(self._key(sensor_id, rule_id), payload)

    async def bump_ok_streak(self, sensor_id: UUID, rule_id: UUID) -> int:
        state = await self.get_state(sensor_id, rule_id)
        if state is None:
            return 0
        ok_streak = state["ok_streak"] + 1
        await self.set_open(
            sensor_id=sensor_id,
            rule_id=rule_id,
            alert_id=UUID(state["alert_id"]),
            ok_streak=ok_streak,
            last_update_sent_at=self._parse_ts(state.get("last_update_sent_at")),
        )
        return ok_streak

    async def clear(self, sensor_id: UUID, rule_id: UUID) -> None:
        await self.delete(self._key(sensor_id, rule_id))

    async def clear_by_rule(self, rule_id: UUID) -> None:
        pattern = ALERT_STATE_KEY.format(sensor_id="*", rule_id=rule_id)
        async for key in self.redis.scan_iter(match=pattern):
            key_str = key.decode() if isinstance(key, bytes) else key
            await self.delete(key_str)

    @staticmethod
    def _parse_ts(value: str | None) -> datetime | None:
        if not value:
            return None
        ts = datetime.fromisoformat(value)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
