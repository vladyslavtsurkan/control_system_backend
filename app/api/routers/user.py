from fastapi import APIRouter

from app.api.dependencies import current_user, SQLUnitOfWorkDep, user_service
from app.schemas import UserResponse, UserUpdateRequest

__all__ = ["router"]

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, status_code=200)
async def me(user: current_user):
    """Get the current user's information."""
    return user


@router.patch("/", response_model=UserResponse, status_code=200)
async def update_me(uow: SQLUnitOfWorkDep, user: current_user, request: UserUpdateRequest, service: user_service):
    """Update the current user's information."""
    return await service.update_user(uow=uow, current_user=user, request=request)
