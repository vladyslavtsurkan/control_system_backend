from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.models import Organization
from app.models.collector_api_key import CollectorApiKey
from app.models.opc_server import OpcServer
from app.models.sensor import Sensor
from app.repositories.base import BaseRepository

__all__ = ["CollectorApiKeyRepository"]


class CollectorApiKeyRepository(BaseRepository[CollectorApiKey]):
    model = CollectorApiKey

    async def get_by_opc_server_id(self, opc_server_id: UUID) -> CollectorApiKey | None:
        return await self.get(filters={"opc_server_id": opc_server_id})

    async def count_by_opc_server_id(self, opc_server_id: UUID) -> int:
        """Return the number of API keys currently issued for an OPC server."""
        statement = select(func.count()).where(CollectorApiKey.opc_server_id == opc_server_id)
        result = await self._session.execute(statement)
        return result.scalar() or 0

    async def get_all_by_organization(self, organization_id: UUID) -> Sequence[CollectorApiKey]:
        """
        Fetch all API keys for OPC servers belonging to a given organization
        in a single query (join CollectorApiKey → OpcServer filtered by org).
        """
        query = (
            select(CollectorApiKey)
            .join(OpcServer, CollectorApiKey.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(
                OpcServer.organization_id == organization_id,
                OpcServer.is_deleted.is_(False),
                Organization.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_by_key_id_with_server_and_sensors(self, key_id: str) -> CollectorApiKey | None:
        """
        Fetch a CollectorApiKey by key_id, eagerly loading its OpcServer
        and only non-deleted Sensors in a single optimised DB round-trip.
        """
        query = (
            select(CollectorApiKey)
            .join(OpcServer, CollectorApiKey.opc_server_id == OpcServer.id)
            .join(Organization, OpcServer.organization_id == Organization.id)
            .where(CollectorApiKey.key_id == key_id)
            .where(OpcServer.is_deleted.is_(False), Organization.is_deleted.is_(False))
            .options(
                joinedload(CollectorApiKey.opc_server).selectinload(
                    OpcServer.sensors.and_(Sensor.is_deleted.is_(False))
                ),
            )
        )
        result = await self._session.execute(query)
        return result.scalars().first()
