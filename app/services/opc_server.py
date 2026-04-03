from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.opc_server import (
    OpcServerCreateRequest,
    OpcServerUpdateRequest,
    OpcServerResponse,
    ApiKeyCreateResponse,
    ApiKeyInfoResponse,
)
from app.schemas.user import UserResponse
from app.services.mixins import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork
from app.utils.api_key_manager import api_key_manager
from app.utils.crypto_manager import crypto_manager

__all__ = ["OpcServerService"]


class OpcServerService(TenantValidationMixin):
    @staticmethod
    async def _get_opc_server_or_404(uow: SQLUnitOfWork, server_id: UUID, tenant_id: UUID):
        """Get an OPC server or raise 404."""
        server = await uow.opc_server.get(filters={"id": server_id, "is_deleted": False, "organization_id": tenant_id})
        if not server:
            raise ObjectNotFoundException(str(server_id), "OpcServer")
        return server

    async def create_opc_server(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        request: OpcServerCreateRequest,
    ) -> OpcServerResponse:
        """Create a new OPC server for the tenant. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

            data = request.model_dump(exclude={"password"})
            data["organization_id"] = tenant_id

            if request.password:
                data["encrypted_password"] = crypto_manager.encrypt(request.password)

            opc_server = await uow.opc_server.create(data)
            return OpcServerResponse.model_validate(opc_server)

    @staticmethod
    async def get_opc_servers(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[OpcServerResponse]:
        """Get all OPC servers for the tenant."""
        async with uow:
            servers, count = await uow.opc_server.get_multi(
                offset=offset,
                limit=limit,
                is_deleted=False,
                organization_id=tenant_id,
            )
            return PaginatedResponse(
                items=[OpcServerResponse.model_validate(s) for s in servers],
                count=count,
                per_page=limit,
            )

    @staticmethod
    async def get_opc_server(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        server_id: UUID,
    ) -> OpcServerResponse:
        """Get a specific OPC server by ID."""
        async with uow:
            server = await uow.opc_server.get(
                filters={"id": server_id, "is_deleted": False, "organization_id": tenant_id}
            )
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")
            return OpcServerResponse.model_validate(server)

    async def get_api_keys(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
    ) -> list[ApiKeyInfoResponse]:
        """
        Get all API keys for OPC servers belonging to the tenant. Only admin/owner.
        The secret keys are not included in the response, only metadata.
        """
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            keys = await uow.collector_api_key.get_all_by_organization(tenant_id)
            return [ApiKeyInfoResponse.model_validate(k) for k in keys]

    async def update_opc_server(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        server_id: UUID,
        current_user: UserResponse,
        request: OpcServerUpdateRequest,
    ) -> OpcServerResponse:
        """Update an OPC server. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

            updates = request.model_dump(exclude_unset=True, exclude={"password"})

            if request.password:
                updates["encrypted_password"] = crypto_manager.encrypt(request.password)

            server = await uow.opc_server.update(
                filters={"id": server_id, "is_deleted": False, "organization_id": tenant_id},
                updates=updates,
            )
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")
            return OpcServerResponse.model_validate(server)

    async def delete_opc_server(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        server_id: UUID,
        current_user: UserResponse,
    ) -> None:
        """Soft delete an OPC server. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

            server = await uow.opc_server.update(
                filters={"id": server_id, "is_deleted": False, "organization_id": tenant_id},
                updates={"is_deleted": True},
            )
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")

    async def create_or_rotate_api_key(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        server_id: UUID,
        current_user: UserResponse,
    ) -> ApiKeyCreateResponse:
        """Create or rotate an API key for an OPC server. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            await self._get_opc_server_or_404(uow, server_id, tenant_id)

            full_key, key_prefix, hashed_key = api_key_manager.generate()

            record = await uow.collector_api_key.create_or_update(
                obj_in={
                    "organization_id": tenant_id,
                    "opc_server_id": server_id,
                    "key_prefix": key_prefix,
                    "hashed_key": hashed_key,
                },
                conflict_columns=["opc_server_id"],
                update_columns=["key_prefix", "hashed_key", "organization_id"],
            )
            return ApiKeyCreateResponse(
                key_prefix=key_prefix,
                secret_key=full_key,
                created_at=record.created_at,
            )

    async def revoke_api_key(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        server_id: UUID,
        current_user: UserResponse,
    ) -> None:
        """Revoke (delete) the API key for an OPC server. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            await self._get_opc_server_or_404(uow, server_id, tenant_id)

            existing = await uow.collector_api_key.get_by_opc_server_id(server_id)
            if not existing:
                raise ObjectNotFoundException(str(server_id), "CollectorApiKey")

            await uow.collector_api_key.delete(filters={"opc_server_id": server_id})
