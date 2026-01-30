from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.opc_server import router as opc_server_router
from app.api.routers.organization import router as organization_router
from app.api.routers.reading import readings_router, alerts_router
from app.api.routers.sensor import router as sensor_router
from app.api.routers.user import router as user_router

__all__ = ["router"]

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(user_router)
router.include_router(organization_router)
router.include_router(opc_server_router)
router.include_router(sensor_router)
router.include_router(readings_router)
router.include_router(alerts_router)
