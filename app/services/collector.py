from datetime import datetime, timezone

from app.core.constants import API_KEY_PREFIX
from app.core.exc import NotAuthorizedException
from app.schemas.collector import CollectorConfigResponse, CollectorSensorResponse
from app.uow.sql import SQLUnitOfWork
from app.utils.api_key_manager import api_key_manager
from app.utils.crypto_manager import crypto_manager

__all__ = ["CollectorService"]


class CollectorService:
    @staticmethod
    async def get_config(uow: SQLUnitOfWork, api_key: str) -> CollectorConfigResponse:
        """
        Authenticate the collector by X-API-Key and return the full
        OPC-server configuration together with its active sensors.

        The key_prefix stored in the DB has the form ``API_KEY_PREFIX``
        (first 8 characters of the random part + ``...``).  We derive the
        same prefix from the incoming key so we can locate the single
        matching row before running the expensive Argon2 verification.
        """
        if not api_key.startswith(API_KEY_PREFIX):
            raise NotAuthorizedException

        raw_part = api_key[len(API_KEY_PREFIX) :]
        key_prefix = f"{API_KEY_PREFIX}{raw_part[:8]}..."

        async with uow:
            record = await uow.collector_api_key.get_by_prefix_with_server_and_sensors(key_prefix)

            if record is None or not api_key_manager.verify(api_key, record.hashed_key):
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
