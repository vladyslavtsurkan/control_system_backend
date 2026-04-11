from datetime import datetime, timezone

from app.core.exc import NotAuthorizedException
from app.schemas.collector import CollectorConfigResponse, CollectorSensorResponse
from app.uow.sql import SQLUnitOfWork
from app.utils.api_key_manager import api_key_manager
from app.utils.crypto_manager import crypto_manager

__all__ = ["CollectorService"]


class CollectorService:
    @staticmethod
    async def get_config(uow: SQLUnitOfWork, api_key_id: str, api_key_secret: str) -> CollectorConfigResponse:
        """
        Authenticate the collector by X-API-Key-ID / X-API-Key-Secret headers and
        return the full OPC-server configuration together with its active sensors.

        Lookup is done by the cheap key_id index first; the expensive Argon2
        verification runs only if a matching row is found.
        """
        async with uow:
            record = await uow.collector_api_key.get_by_key_id_with_server_and_sensors(api_key_id)

            if record is None or not api_key_manager.verify(api_key_secret, record.hashed_key):
                raise NotAuthorizedException

            # Update last_used_at
            await uow.collector_api_key.update(
                filters={"id": record.id},
                updates={"last_used_at": datetime.now(timezone.utc)},
            )

            server = record.opc_server

            password: str | None = None
            if server.encrypted_password:
                password = crypto_manager.decrypt(server.encrypted_password)

            return CollectorConfigResponse(
                id=server.id,
                name=server.name,
                url=server.url,
                security_policy=server.security_policy,
                authentication_method=server.authentication_method,
                username=server.username,
                password=password,
                sensors=[CollectorSensorResponse.model_validate(s) for s in server.sensors],
            )
