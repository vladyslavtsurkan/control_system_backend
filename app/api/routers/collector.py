from fastapi import APIRouter, Security, status
from fastapi.security import APIKeyHeader

from app.api.dependencies import AdminUnitOfWorkDep, collector_service
from app.schemas.collector import CollectorConfigResponse

__all__ = ["router"]

_api_key_header = APIKeyHeader(name="X-API-Key")

router = APIRouter(prefix="/collector", tags=["Collector"])


@router.get("/config", response_model=CollectorConfigResponse, status_code=status.HTTP_200_OK)
async def get_collector_config(
    uow: AdminUnitOfWorkDep,
    service: collector_service,
    api_key: str = Security(_api_key_header),
):
    """
    Return the full OPC-server configuration and its active sensors.

    Authenticated via the ``X-API-Key`` header (collector API key).
    """
    return await service.get_config(uow=uow, api_key=api_key)
