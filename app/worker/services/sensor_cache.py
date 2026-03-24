from uuid import UUID

from app.uow.sql import SQLUnitOfWork
from app.uow.redis import RedisUnitOfWork


class SensorCacheService:
    @staticmethod
    async def get_organizations_by_sensor_ids(sensor_ids: set[UUID]) -> dict[UUID, UUID]:
        if not sensor_ids:
            return {}

        async with RedisUnitOfWork() as redis_uow:
            cached_orgs = await redis_uow.sensor_org.get_orgs_by_sensor_ids(sensor_ids)
            missing_sensor_ids = sensor_ids - cached_orgs.keys()

        if not missing_sensor_ids:
            return cached_orgs

        async with SQLUnitOfWork(bypass_rls=True) as uow:
            organizations_by_sensor = await uow.sensor.get_orgs_by_ids(missing_sensor_ids)

        if organizations_by_sensor:
            async with RedisUnitOfWork() as redis_uow:
                await redis_uow.sensor_org.set_orgs_by_sensor_ids(organizations_by_sensor)

        return cached_orgs | organizations_by_sensor
