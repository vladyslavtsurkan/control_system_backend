from typing import Annotated

from fastapi import Depends, Query

from app.core.constants import PAGINATION_PER_PAGE
from app.services.auth import AuthService
from app.services.organization import OrganizationService
from app.services.user import UserService
from app.uow.base import ABCUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = [
    "SQLUnitOfWorkDep",
    "user_service",
    "auth_service",
    "current_user",
    "organization_service",
    "offset_query",
    "limit_query",
]

SQLUnitOfWorkDep = Annotated[ABCUnitOfWork, Depends(SQLUnitOfWork)]
user_service = Annotated[UserService, Depends(UserService)]
auth_service = Annotated[AuthService, Depends(AuthService)]
current_user = Annotated[UserService, Depends(AuthService.get_current_user)]
organization_service = Annotated[OrganizationService, Depends(OrganizationService)]

offset_query = Query(0, ge=0, description="Number of items to skip")
limit_query = Query(PAGINATION_PER_PAGE, ge=1, le=100, description="Number of items to return")
