from uuid import UUID

from app.core.constants import SENSOR_ORG_TTL_SECONDS
from app.repositories.redis.base import BaseRedisRepository

SENSOR_ORG_KEY = "sensor_org:{sensor_id}"


class SensorOrgRepository(BaseRedisRepository):
    DEFAULT_TTL_SECONDS = SENSOR_ORG_TTL_SECONDS

    async def get_orgs_by_sensor_ids(self, sensor_ids: set[UUID]) -> dict[UUID, UUID]:
        key_by_sensor_id = {sensor_id: SENSOR_ORG_KEY.format(sensor_id=str(sensor_id)) for sensor_id in sensor_ids}
        values_by_key = await self.mget_raw(list(key_by_sensor_id.values()))

        result = {}
        for sensor_id, key in key_by_sensor_id.items():
            value = values_by_key.get(key)
            if value is not None:
                try:
                    result[sensor_id] = UUID(value)
                except ValueError:
                    continue
        return result

    async def set_orgs_by_sensor_ids(self, organizations_by_sensor: dict[UUID, UUID]) -> None:
        values_by_key = {
            SENSOR_ORG_KEY.format(sensor_id=str(sensor_id)): str(org_id)
            for sensor_id, org_id in organizations_by_sensor.items()
        }
        await self.mset_raw(values_by_key, ttl_seconds=self.DEFAULT_TTL_SECONDS)
