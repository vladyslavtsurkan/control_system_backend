from fastapi import APIRouter, Security, status
from fastapi.security import APIKeyHeader

from app.api.dependencies import AdminUnitOfWorkDep, collector_service
from app.schemas.collector import CollectorConfigResponse

__all__ = ["router"]

_api_key_id_header = APIKeyHeader(name="X-API-Key-ID", description="Public API key identifier")
_api_key_secret_header = APIKeyHeader(name="X-API-Key-Secret", description="API key secret")

router = APIRouter(prefix="/collector", tags=["Collector"])


@router.get("/config", response_model=CollectorConfigResponse, status_code=status.HTTP_200_OK)
async def get_collector_config(
    uow: AdminUnitOfWorkDep,
    service: collector_service,
    api_key_id: str = Security(_api_key_id_header),
    api_key_secret: str = Security(_api_key_secret_header),
):
    """
    Return the full OPC-server configuration and its active sensors.

    Authenticated via the ``X-API-Key-ID`` and ``X-API-Key-Secret`` headers.
    Both headers are required. The ID is used to look up the key record; the
    secret is verified against the stored Argon2 hash.
    """
    return await service.get_config(uow=uow, api_key_id=api_key_id, api_key_secret=api_key_secret)
