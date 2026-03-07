from uuid import UUID

from app.models.opc_server import CollectorApiKey
from app.repositories.base import BaseRepository

__all__ = ["CollectorApiKeyRepository"]


class CollectorApiKeyRepository(BaseRepository[CollectorApiKey]):
    model = CollectorApiKey

    async def get_by_opc_server_id(self, opc_server_id: UUID) -> CollectorApiKey | None:
        return await self.get(filters={"opc_server_id": opc_server_id})
