from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.user import router as user_router

__all__ = ["router"]

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(user_router)
