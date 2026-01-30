from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.opc_server import (
    OpcServerCreateRequest,
    OpcServerUpdateRequest,
    OpcServerResponse,
)
from app.uow.sql import SQLUnitOfWork
from app.utils.hash_manager import hash_manager

__all__ = ["OpcServerService"]


class OpcServerService:
    @staticmethod
    async def create_opc_server(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        request: OpcServerCreateRequest,
    ) -> OpcServerResponse:
        """Create a new OPC server for the tenant."""
        async with uow:
            data = request.model_dump(exclude={"password"})
            data["organization_id"] = tenant_id

            if request.password:
                data["encrypted_password"] = hash_manager.get_hash(request.password)

            opc_server = await uow.opc_server.create(data)
            return OpcServerResponse.model_validate(opc_server)

    @staticmethod
    async def get_opc_servers(
        uow: SQLUnitOfWork,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[OpcServerResponse]:
        """Get all OPC servers for the tenant (filtered by RLS)."""
        async with uow:
            servers, count = await uow.opc_server.get_multi(
                offset=offset,
                limit=limit,
                is_deleted=False,
            )
            return PaginatedResponse(
                items=[OpcServerResponse.model_validate(s) for s in servers],
                count=count,
                per_page=limit,
            )

    @staticmethod
    async def get_opc_server(
        uow: SQLUnitOfWork,
        server_id: UUID,
    ) -> OpcServerResponse:
        """Get a specific OPC server by ID."""
        async with uow:
            server = await uow.opc_server.get(filters={"id": server_id, "is_deleted": False})
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")
            return OpcServerResponse.model_validate(server)

    @staticmethod
    async def update_opc_server(
        uow: SQLUnitOfWork,
        server_id: UUID,
        request: OpcServerUpdateRequest,
    ) -> OpcServerResponse:
        """Update an OPC server."""
        async with uow:
            updates = request.model_dump(exclude_unset=True, exclude={"password"})

            if request.password:
                updates["encrypted_password"] = hash_manager.get_hash(request.password)

            server = await uow.opc_server.update(
                filters={"id": server_id, "is_deleted": False},
                updates=updates,
            )
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")
            return OpcServerResponse.model_validate(server)

    @staticmethod
    async def delete_opc_server(
        uow: SQLUnitOfWork,
        server_id: UUID,
    ) -> None:
        """Soft delete an OPC server."""
        async with uow:
            server = await uow.opc_server.update(
                filters={"id": server_id, "is_deleted": False},
                updates={"is_deleted": True},
            )
            if not server:
                raise ObjectNotFoundException(str(server_id), "OpcServer")
