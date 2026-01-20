from typing import Annotated

from fastapi import Depends

from app.services.auth import AuthService
from app.services.user import UserService
from app.uow.base import ABCUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = [
    "SQLUnitOfWorkDep",
    "user_service",
    "auth_service",
    "current_user",
]

SQLUnitOfWorkDep = Annotated[ABCUnitOfWork, Depends(SQLUnitOfWork)]
user_service = Annotated[UserService, Depends(UserService)]
auth_service = Annotated[AuthService, Depends(AuthService)]
current_user = Annotated[UserService, Depends(AuthService.get_current_user)]
