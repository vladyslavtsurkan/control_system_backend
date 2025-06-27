from typing import Annotated

from fastapi import Depends

from app.uow.base import ABCUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = [
    "SQLUnitOfWorkDep",
]

SQLUnitOfWorkDep = Annotated[ABCUnitOfWork, Depends(SQLUnitOfWork)]
