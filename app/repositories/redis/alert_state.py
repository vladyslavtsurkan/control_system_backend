from datetime import datetime, timezone
from uuid import UUID

from app.core.constants import REDIS_ALERT_STATE_TTL_SECONDS
from app.repositories.redis.base import BaseRedisRepository
from app.repositories.redis.types import PendingMutation

__all__ = ["AlertStateRepository"]

ALERT_STATE_KEY = "alert_state:{sensor_id}:{rule_id}"
ALERT_PENDING_KEY = "alert:pending:{rule_id}:{sensor_id}"


class AlertStateRepository(BaseRedisRepository):
    """
    Stores transient alert lifecycle state per ``sensor_id + rule_id``.

    This state is intentionally ephemeral; if Redis is flushed, the worker
    rebuilds state from subsequent telemetry messages.
    """

    DEFAULT_TTL_SECONDS = REDIS_ALERT_STATE_TTL_SECONDS

    async def get_state(self, sensor_id: UUID, rule_id: UUID) -> dict | None:
        key = ALERT_STATE_KEY.format(sensor_id=sensor_id, rule_id=rule_id)
        state = await self.get(key)
        if state is None:
            return None

        return {
            "alert_id": state.get("alert_id"),
            "status": state.get("status", "open"),
            "ok_streak": int(state.get("ok_streak", "0")),
            "last_update_sent_at": state.get("last_update_sent_at"),
        }

    async def get_states_bulk(self, pairs: list[tuple[UUID, UUID]]) -> dict[tuple[UUID, UUID], dict | None]:
        unique_pairs = list(dict.fromkeys(pairs))
        if not unique_pairs:
            return {}

        keys = [ALERT_STATE_KEY.format(sensor_id=sensor_id, rule_id=rule_id) for sensor_id, rule_id in unique_pairs]
        pipe = self.redis.pipeline(transaction=False)
        for key in keys:
            await pipe.hgetall(key)
        rows = await pipe.execute()

        result: dict[tuple[UUID, UUID], dict | None] = {}
        for pair, row in zip(unique_pairs, rows):
            if not row:
                result[pair] = None
                continue
            state = self._decode_bytes(row)
            result[pair] = {
                "alert_id": state.get("alert_id"),
                "status": state.get("status", "open"),
                "ok_streak": int(state.get("ok_streak", "0")),
                "last_update_sent_at": state.get("last_update_sent_at"),
            }
        return result

    async def set_open(
        self,
        sensor_id: UUID,
        rule_id: UUID,
        alert_id: UUID,
        ok_streak: int = 0,
        last_update_sent_at: datetime | None = None,
    ) -> None:
        key = ALERT_STATE_KEY.format(sensor_id=sensor_id, rule_id=rule_id)
        payload = {
            "alert_id": str(alert_id),
            "status": "open",
            "ok_streak": str(ok_streak),
            "last_update_sent_at": last_update_sent_at.isoformat() if last_update_sent_at else "",
        }
        await self.set(key, payload)

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
        key = ALERT_STATE_KEY.format(sensor_id=sensor_id, rule_id=rule_id)
        await self.delete(key)

    async def get_pending(self, sensor_id: UUID, rule_id: UUID) -> float | None:
        key = ALERT_PENDING_KEY.format(rule_id=rule_id, sensor_id=sensor_id)
        value = await self.get_raw(key)
        if value is None:
            return None

        try:
            return float(value)
        except TypeError, ValueError:
            await self.clear_pending(sensor_id, rule_id)
            return None

    async def get_pending_bulk(self, pairs: list[tuple[UUID, UUID]]) -> dict[tuple[UUID, UUID], float | None]:
        unique_pairs = list(dict.fromkeys(pairs))
        if not unique_pairs:
            return {}

        keys = [ALERT_PENDING_KEY.format(rule_id=rule_id, sensor_id=sensor_id) for sensor_id, rule_id in unique_pairs]
        pipe = self.redis.pipeline(transaction=False)
        for key in keys:
            await pipe.get(key)
        values = await pipe.execute()

        result: dict[tuple[UUID, UUID], float | None] = {}
        invalid_keys: list[str] = []
        for pair, key, value in zip(unique_pairs, keys, values):
            decoded = self._decode_value(value)
            if decoded is None:
                result[pair] = None
                continue
            try:
                result[pair] = float(decoded)
            except TypeError, ValueError:
                result[pair] = None
                invalid_keys.append(key)

        if invalid_keys:
            cleanup_pipe = self.redis.pipeline(transaction=False)
            for key in invalid_keys:
                await cleanup_pipe.delete(key)
            await cleanup_pipe.execute()

        return result

    async def set_pending(self, sensor_id: UUID, rule_id: UUID, first_spike_ts: float, ttl_seconds: int) -> None:
        key = ALERT_PENDING_KEY.format(rule_id=rule_id, sensor_id=sensor_id)
        await self.set_raw(key, str(first_spike_ts), ttl_seconds=ttl_seconds)

    async def clear_pending(self, sensor_id: UUID, rule_id: UUID) -> None:
        key = ALERT_PENDING_KEY.format(rule_id=rule_id, sensor_id=sensor_id)
        await self.delete(key)

    async def bulk_update_pending(self, mutations: list[PendingMutation]) -> None:
        if not mutations:
            return

        pipe = self.redis.pipeline(transaction=False)
        for mutation in mutations:
            key = ALERT_PENDING_KEY.format(rule_id=mutation["rule_id"], sensor_id=mutation["sensor_id"])
            first_spike_ts = mutation["first_spike_ts"]
            if first_spike_ts is None:
                await pipe.delete(key)
                continue

            ttl_seconds = mutation.get("ttl_seconds")
            if ttl_seconds is None:
                await pipe.set(key, str(first_spike_ts))
            else:
                await pipe.set(key, str(first_spike_ts), ex=ttl_seconds)

        await pipe.execute()

    async def clear_by_rule(self, rule_id: UUID) -> None:
        pattern = ALERT_STATE_KEY.format(sensor_id="*", rule_id=rule_id)
        await self.delete_by_pattern(pattern)

        await self.clear_pending_by_rule(rule_id)

    async def clear_pending_by_rule(self, rule_id: UUID) -> None:
        pattern = ALERT_PENDING_KEY.format(rule_id=rule_id, sensor_id="*")
        await self.delete_by_pattern(pattern)

    @staticmethod
    def _parse_ts(value: str | None) -> datetime | None:
        if not value:
            return None
        ts = datetime.fromisoformat(value)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
